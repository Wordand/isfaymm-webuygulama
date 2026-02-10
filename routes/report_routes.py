from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, current_app
from services.db import get_conn
from services.utils import prepare_df, to_float_turkish, month_key
from services.pdf_service import SECTION_KEYS, SECTION_ALIASES
from extensions import fernet
from finansal_oranlar import hesapla_finansal_oranlar, analiz_olustur
from auth import login_required
import pandas as pd
import json
import psycopg2.extras
import io
import re
import os
import shutil
import tempfile
import pdfkit
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote
from collections import OrderedDict
import unicodedata

bp = Blueprint('report', __name__)

# --- KDV Helpers ---

# Satır sıralaması için öncelik haritası (Sayfa 1 Sırasına Göre)
ROW_ORDER_PRIORITY = {
    # MATRAH
    "Toplam Matrah": 1, 
    "Hesaplanan KDV": 2, 
    "Daha Önce İndirim Konusu Yapılan KDV'nin İlavesi": 3, 
    "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi": 3, 
    "Toplam KDV": 4,
    # SONUÇ HESAPLARI
    "Tecil Edilecek KDV": 1, 
    "Ödenmesi Gereken KDV": 2, 
    "İade Edilmesi Gereken KDV": 3, 
    "Sonraki Döneme Devreden KDV": 4,
    # DİĞER BİLGİLER
    "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Aylık)": 1,
    "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)": 2,
    "Kredi Kartı İle Tahsil Edilen": 3
}

CANON_SECTIONS = [
    "MATRAH",
    "MATRAH DETAYI",
    "İNDİRİMLER",
    "İNDİRİMLER DETAYI",
    "İSTİSNALAR VE İADE",
    "SONUÇ HESAPLARI",
    "DİĞER BİLGİLER",
]

def _u(s):
    return (s or "").upper().replace("İ","I").replace("Ş","S").replace("Ğ","G").replace("Ü","U").replace("Ö","O").replace("Ç","C")

def classify_section(key: str) -> str:
    u = _u(key).strip()
    if key.startswith("§ "): return key[2:].strip()
    
    # 1. Kodlu Detay Kalemleri (Sayfa 2-3)
    if re.match(r"^(1100|616|504|113|114|115|116|117|118|119|120)\b", u): return "MATRAH DETAYI"
    if re.match(r"^(103|108|109|110)\b", u) or "INDIRIM (% " in u or "ONCEKI DONEMDEN DEVREDEN KDV" in u:
        return "İNDİRİMLER DETAYI"
    if re.match(r"^(301|302|303|304|338|450)\b", u) or "TESLIM TUTARI" in u or "YUKLENILEN KDV" in u or "IADEYE KONU" in u:
        return "İSTİSNALAR VE İADE"

    # 2. Özet Başlıklar (Sayfa 1)
    if any(x in u for x in ["TOPLAM MATRAH", "HESAPLANAN KDV", "ILAVESI", "TOPLAM KDV"]): return "MATRAH"
    if "INDIRIMLER TOPLAMI" in u: return "İNDİRİMLER"
    if any(x in u for x in ["SONRAKI DONEME DEVREDEN", "ODENMESI GEREKEN", "IADE EDILMESI GEREKEN", "TECIL EDILECEK"]):
        return "SONUÇ HESAPLARI"
    if any(x in u for x in ["BEDEL (AYLIK)", "BEDEL (KUMULATIF)", "KREDI KARTI"]): return "DİĞER BİLGİLER"
    if "ISTISNA" in u or "IADE EDILEBILIR" in u or "ISTISNALARA ILISKIN BILGILER" in u: return "İSTİSNALAR VE İADE"

    return "MATRAH DETAYI"

def normalize_row_key(key: str) -> str:
    if key.startswith("§ "): return key
    return re.sub(r"[,\s]+", " ", key).strip()

def consolidate_kdv_rows(kdv_data: dict) -> dict:
    out = {}
    for key, cols in kdv_data.items():
        canon = normalize_row_key(key)
        dest = out.setdefault(canon, {})
        for m, v in cols.items():
            if not dest.get(m) or str(dest[m]).strip() in ("", "nan", "None", "-"):
                dest[m] = "" if v is None else str(v)
    return out

def reorder_by_section(kdv_data: dict) -> "OrderedDict[str, dict]":
    # 1. Consolidate and Classify with Normalization
    unique_data = OrderedDict()
    for k, v in kdv_data.items():
        norm_k = normalize_row_key(k)
        # If a normalized key already exists, we assume the first one encountered is sufficient
        # or we could merge values if needed, but for now, just take the first.
        if norm_k not in unique_data:
            unique_data[norm_k] = v
        else:
            # If the original key is different but normalized key is same,
            # we might want to merge values if one has more complete data.
            # For simplicity, we'll just keep the first one for now.
            pass

    buckets = {sec: [] for sec in CANON_SECTIONS}
    for key in unique_data:
        if key.startswith("§ "): continue
        sec = classify_section(key)
        if sec in buckets: buckets[sec].append(key)
    
    out = OrderedDict()
    for sec in CANON_SECTIONS:
        rows = buckets[sec]
        if rows or sec in ["MATRAH", "İNDİRİMLER", "SONUÇ HESAPLARI"]: # Önemli başlıklar boş olsa da gelsin
            out[f"§ {sec}"] = {} 
            for r in sorted(rows): # Satırları kendi içinde sırala
                out[r] = kdv_data[r]
    return out

# --- Routes ---

@bp.route("/raporlama")
@login_required
def raporlama():
    vkn = request.args.get("vkn")
    fa_years = [y for y in request.args.get("fa_years", "").split(",") if y]
    kdv_periods = [d for d in request.args.get("kdv_periods", "").split(",") if d]
    analiz_turu = request.args.get("analiz_turu")

    unvanlar, donemler, grafik_listesi, yuklenen_dosyalar = [], [], [], []
    secili_unvan = None
    uid = session.get("user_id")

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT vergi_kimlik_no, unvan FROM mukellef WHERE user_id=%s ORDER BY unvan", (uid,))
        unvanlar = [{"vkn": row["vergi_kimlik_no"], "unvan": row["unvan"]} for row in c.fetchall()]

        if vkn:
            c.execute("SELECT unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, uid))
            row = c.fetchone()
            if row: secili_unvan = row["unvan"]

            c.execute("SELECT DISTINCT b.donem FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.vergi_kimlik_no=%s AND m.user_id=%s ORDER BY b.donem DESC", (vkn, uid))
            donemler = sorted(set(r["donem"] for r in c.fetchall()), reverse=True)

            c.execute("SELECT b.tur, b.yuklenme_tarihi, b.donem FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.vergi_kimlik_no=%s AND m.user_id=%s ORDER BY b.yuklenme_tarihi DESC", (vkn, uid))
            for r in c.fetchall():
                yuklenen_dosyalar.append({"tur": r["tur"], "tarih": str(r["yuklenme_tarihi"]), "donem": r["donem"]})

    if vkn and analiz_turu == "kdv" and kdv_periods:
        return redirect(url_for("report.rapor_kdv", vkn=vkn, unvan=secili_unvan, kdv_periods=",".join(kdv_periods)))

    return render_template("reports/raporlama.html", mukellefler=unvanlar, donemler=donemler, secili_vkn=vkn, secili_unvan=secili_unvan, secili_fa_years=fa_years, secili_kdv_periods=kdv_periods, analiz_turu=analiz_turu, yuklenen_dosyalar=yuklenen_dosyalar, grafik_listesi=grafik_listesi)

@bp.route("/raporlama-grafik")
@login_required
def raporlama_grafik():
    # Grafik oluşturma isteğini raporlama sayfasına yönlendir (filtreleri koruyarak)
    return redirect(url_for('report.raporlama', **request.args))


@bp.route("/finansal-oran-raporu")
@login_required
def finansal_oran_raporu():
    # Finansal oran raporu isteğini (PDF/Excel) şimdilik analiz sayfasına yönlendir
    return redirect(url_for('report.finansal_analiz', **request.args))


@bp.route("/rapor-kdv")
@login_required
def rapor_kdv():
    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan")
    donemler = [d for d in request.args.get("kdv_periods", "").split(",") if d]
    
    if not vkn or not donemler:
        flash("Mükellef ve dönem seçilmelidir.", "warning")
        return redirect(url_for("report.raporlama"))

    kdv_data, kdv_months = {}, []
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for donem in donemler:
            c.execute("SELECT b.veriler, b.donem FROM beyanname b JOIN mukellef m ON m.id = b.mukellef_id WHERE m.vergi_kimlik_no=%s AND b.donem=%s AND b.tur='kdv'", (vkn, donem))
            rows = c.fetchall()
            for row in rows:
                try:
                    data_bytes = row["veriler"].tobytes() if isinstance(row["veriler"], memoryview) else row["veriler"]
                    parsed = json.loads(fernet.decrypt(data_bytes).decode("utf-8"))
                    raw_donem = parsed.get("donem") or row["donem"]
                    ay, yil = [p.strip() for p in raw_donem.split("/") if p.strip()]
                    col = f"{yil}/{ay.upper()}"
                    if col not in kdv_months: kdv_months.append(col)
                    for rec in parsed.get("veriler", []):
                        kdv_data.setdefault(rec["alan"], {})[col] = rec["deger"]
                except Exception as e: print(e)

    kdv_months = sorted(set(kdv_months), key=month_key)
    
    # --- Summary Metrics & Validation ---
    kdv_summary = {m: {"matrah": 0, "hesaplanan": 0, "indirim": 0, "devreden": 0, "odenecek": 0, "iade": 0} for m in kdv_months}
    inconsistencies = []
    
    # Track sub-totals for validation
    calc_checks = {m: {"sub_matrah": 0, "sub_kdv": 0} for m in kdv_months}

    for alan, aylik in kdv_data.items():
        u_alan = _u(alan)
        for m, v in aylik.items():
            val = to_float_turkish(v) or 0
            # KPI Extraction
            if "MATRAH TOPLAMI" in u_alan: kdv_summary[m]["matrah"] = val
            elif "HESAPLANAN KDV" in u_alan or "TOPLAM KDV" in u_alan: kdv_summary[m]["hesaplanan"] = val
            elif "INDIRIMLER TOPLAMI" in u_alan: kdv_summary[m]["indirim"] = val
            elif "SONRAKI DONEME DEVREDEN" in u_alan: kdv_summary[m]["devreden"] = val
            elif "ODENMESI GEREKEN" in u_alan: kdv_summary[m]["odenecek"] = val
            elif "IADE EDILMESI GEREKEN" in u_alan: kdv_summary[m]["iade"] = val
            
            # Validation Logic: Sum up specific items to check against totals
            if "(%" in u_alan and "- Matrah" in u_alan:
                calc_checks[m]["sub_matrah"] += val
            if "(%" in u_alan and "- Vergi" in u_alan:
                calc_checks[m]["sub_kdv"] += val

    # Perform Cross-Checks
    for m in kdv_months:
        if abs(kdv_summary[m]["matrah"] - calc_checks[m]["sub_matrah"]) > 1.0:
            inconsistencies.append(f"{m} dönemi için Matrah Detayı toplamı ({calc_checks[m]['sub_matrah']:,.2f}) ile Toplam Matrah ({kdv_summary[m]['matrah']:,.2f}) uyumsuz.")
        if abs(kdv_summary[m]["hesaplanan"] - calc_checks[m]["sub_kdv"]) > 1.0:
            inconsistencies.append(f"{m} dönemi için KDV Detayı toplamı ({calc_checks[m]['sub_kdv']:,.2f}) ile Toplam KDV ({kdv_summary[m]['hesaplanan']:,.2f}) uyumsuz.")

    processed_data = reorder_by_section(consolidate_kdv_rows(kdv_data))
    
    return render_template("reports/rapor_kdv.html", 
                           secili_unvan=unvan, 
                           secili_vkn=vkn, 
                           secili_donemler=donemler, 
                           kdv_data=processed_data, 
                           kdv_months=kdv_months,
                           kdv_summary=kdv_summary,
                           inconsistencies=inconsistencies)

@bp.route("/rapor-kdv-excel")
@login_required
def rapor_kdv_excel():
    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan", "M\u00FCkellef")
    donemler_str = request.args.get("donemler", "")
    donemler = [d for d in donemler_str.split(",") if d]

    if not vkn or not donemler:
        flash("M\u00FCkellef ve d\u00F6nem bilgisi eksik.", "warning")
        return redirect(url_for("report.raporlama"))

    kdv_data, kdv_months = {}, []
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for donem in donemler:
            c.execute("""
                SELECT b.veriler, b.donem 
                FROM beyanname b 
                JOIN mukellef m ON m.id = b.mukellef_id 
                WHERE m.vergi_kimlik_no=%s AND b.donem=%s AND b.tur='kdv' AND b.user_id=%s
            """, (vkn, donem, session["user_id"]))
            rows = c.fetchall()
            for row in rows:
                try:
                    data_bytes = row["veriler"].tobytes() if isinstance(row["veriler"], memoryview) else row["veriler"]
                    parsed = json.loads(fernet.decrypt(data_bytes).decode("utf-8"))
                    raw_donem = parsed.get("donem") or row["donem"]
                    # '01/2024' -> parts=['01','2024']
                    parts = [p.strip() for p in raw_donem.split("/") if p.strip()]
                    if len(parts) == 2:
                        # Normalize to 'YEAR/MONTH' for column sorting
                        if parts[1].isdigit() and len(parts[1]) == 4:
                            ay, yil = parts[0], parts[1]
                        else:
                            yil, ay = parts[0], parts[1]
                        col = f"{yil}/{ay.upper()}"
                    else:
                        col = raw_donem
                        
                    if col not in kdv_months: kdv_months.append(col)
                    for rec in parsed.get("veriler", []):
                        kdv_data.setdefault(rec["alan"], {})[col] = rec.get("deger")
                except Exception as e:
                    print(f"Excel Export Error: {e}")

    kdv_months = sorted(set(kdv_months), key=month_key)
    final_data = reorder_by_section(consolidate_kdv_rows(kdv_data))

    rows = []
    for alan, values in final_data.items():
        row = {"A\u00C7IKLAMA": alan}
        for m in kdv_months:
            v = values.get(m)
            # Veri temizleme
            if v is None or str(v).lower() in ['nan', 'none', '-']:
                row[m] = ""
            else:
                row[m] = v
        rows.append(row)

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    
    # xlsxwriter genellikle pandas ile gelir, gelmezse openpyxl dener
    engine = 'xlsxwriter'
    try:
        import xlsxwriter
    except ImportError:
        engine = 'openpyxl'

    with pd.ExcelWriter(output, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name='KDV Ozeti')
        if engine == 'xlsxwriter':
            workbook = writer.book
            worksheet = writer.sheets['KDV Ozeti']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#4e54c8', 'font_color': 'white', 'border': 1})
            section_format = workbook.add_format({'bold': True, 'bg_color': '#f1f5f9', 'font_color': '#4e54c8'})
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            for row_num, row_data in enumerate(rows):
                if row_data["A\u00C7IKLAMA"].startswith("\u00A7 "):
                    worksheet.set_row(row_num + 1, None, section_format)
            
            worksheet.set_column(0, 0, 50)
            worksheet.freeze_panes(1, 1)

    output.seek(0)
    safe_unvan = "".join([c for c in unvan if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
    filename = f"KDV_Ozeti_{safe_unvan}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@bp.route("/tablo-mizan/<string:tur>")
@login_required
def tablo_mizan(tur):
    vkn = request.args.get("vkn")
    donem = request.args.get("donem")
    if not (tur and vkn and donem):
        flash("Eksik parametre.")
        return redirect(url_for("data.veri_giris"))

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=%s", (vkn,))
        row = c.fetchone()
        if not row:
             flash("Mükellef bulunamadı.")
             return redirect(url_for("data.veri_giris"))
        mid, unvan = row["id"], row["unvan"]
        c.execute("SELECT veriler FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur='mizan'", (session["user_id"], mid, donem))
        row = c.fetchone()

    if not row:
        flash("Mizan verisi bulunamadı.")
        return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))

    try:
        data = row["veriler"].tobytes() if isinstance(row["veriler"], memoryview) else row["veriler"]
        mizan_data = json.loads(fernet.decrypt(data).decode("utf-8"))
    except:
        flash("Mizan verisi okunamadı.")
        return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))

    if tur == "bilanco":
         return render_template("tables/tablo_bilanco.html", unvan=unvan, donem=donem, vkn=vkn, aktif_list=mizan_data.get("aktif",[]), pasif_list=mizan_data.get("pasif",[]), toplamlar={}, secilen_donem="cari", donem_mapping={"cari": donem}, has_inflation=False, gorunen_kolon="cari_donem", aktif_alt_toplamlar={}, pasif_alt_toplamlar={})
    elif tur == "gelir":
         return render_template("tables/tablo_gelir.html", tablo=mizan_data.get("gelir",[]), unvan=unvan, donem=donem, vkn=vkn, donem_mapping={"cari": donem}, secilen_donem="cari", gorunen_kolon="cari_donem")
    
    return redirect(url_for("data.veri_giris"))

@bp.route("/finansal-analiz")
@login_required
def finansal_analiz():
    secili_vkn = request.args.get("vkn")
    secili_yillar = request.args.getlist("yillar") or []
    inflation_mode = request.args.get("inflation_mode", "auto")
    kategori = request.args.get("kategori", "likidite")
    
    uid = session.get("user_id")
    unvanlar, mevcut_yillar, trend_data = [], [], {}
    
    uyarilar = []
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT vergi_kimlik_no, unvan FROM mukellef WHERE user_id=%s ORDER BY unvan", (uid,))
        unvanlar = [{"vkn": r["vergi_kimlik_no"], "unvan": r["unvan"]} for r in c.fetchall()]
        
        if secili_vkn:
            # Önce bu mükellefe ait tüm yüklenen belge türlerini çek (Hangi yıllarda ne eksik görmek için)
            c.execute("SELECT donem, tur FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.tur IN ('bilanco', 'gelir')", (uid, secili_vkn))
            existing_docs = c.fetchall()
            docs_by_year = {}
            for row in existing_docs:
                docs_by_year.setdefault(row['donem'], set()).add(row['tur'])

            c.execute("SELECT DISTINCT donem FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.tur='bilanco'", (uid, secili_vkn))
            mevcut_yillar = sorted([r["donem"] for r in c.fetchall()], reverse=True)
            if not secili_yillar: secili_yillar = mevcut_yillar

            for yil in secili_yillar:
                doc_types = docs_by_year.get(yil, set())
                if 'bilanco' not in doc_types or 'gelir' not in doc_types:
                    missing = []
                    if 'bilanco' not in doc_types: missing.append("Bilanço")
                    if 'gelir' not in doc_types: missing.append("Gelir Tablosu")
                    uyarilar.append(f"{yil} yılı için {' ve '.join(missing)} eksik olduğu için analiz hesaplanamadı.")
                    continue

                try:
                    c.execute("SELECT b.veriler FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.donem=%s AND b.tur='bilanco' LIMIT 1", (uid, secili_vkn, yil))
                    rb = c.fetchone()
                    c.execute("SELECT b.veriler FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.donem=%s AND b.tur='gelir' LIMIT 1", (uid, secili_vkn, yil))
                    rg = c.fetchone()
                    if not rb or not rg: continue

                    pb = json.loads(fernet.decrypt(rb["veriler"].tobytes() if isinstance(rb["veriler"], memoryview) else rb["veriler"]).decode("utf-8"))
                    pg = json.loads(fernet.decrypt(rg["veriler"].tobytes() if isinstance(rg["veriler"], memoryview) else rg["veriler"]).decode("utf-8"))

                    aktif_df = prepare_df(pd.DataFrame(pb.get("aktif", [])), "Cari Dönem")
                    pasif_df = prepare_df(pd.DataFrame(pb.get("pasif", [])), "Cari Dönem")
                    gelir_df = prepare_df(pd.DataFrame(pg.get("tablo", [])), "Cari Dönem")
                    
                    oranlar = hesapla_finansal_oranlar(aktif_df, pasif_df, gelir_df, kategori)
                    for k, v in oranlar.items():
                        trend_data.setdefault(k, {})[yil] = float(v.get("deger", 0)) if isinstance(v, dict) else float(v or 0)
                except Exception as e:
                    print(f"Hata ({yil}): {e}")
                    uyarilar.append(f"{yil} yılı analizi sırasında hata oluştu: {str(e)}")
                    
    return render_template("reports/finansal_analiz.html", unvanlar=unvanlar, secili_vkn=secili_vkn, kategori=kategori, mevcut_yillar=mevcut_yillar, secili_yillar=secili_yillar, inflation_mode=inflation_mode, trend_data=trend_data, uyarilar=uyarilar)

@bp.route("/pdf-belgeler-tablo")
@login_required
def pdf_belgeler_tablo():
    vkn = request.args.get("vkn")
    donem = request.args.get("donem")
    tur = request.args.get("tur")
    
    if not (vkn and donem and tur):
        flash("Eksik parametre.")
        return redirect(url_for("data.veri_giris"))

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, session["user_id"]))
        row = c.fetchone()
        if not row:
             flash("Mükellef bulunamadı.")
             return redirect(url_for("data.veri_giris"))
        mid, unvan = row["id"], row["unvan"]
        c.execute("SELECT veriler FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur=%s", (session["user_id"], mid, donem, tur))
        row = c.fetchone()

    if not row:
        flash(f"{tur.upper()} verisi bulunamadı.")
        return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))

    try:
        data_bytes = row["veriler"].tobytes() if isinstance(row["veriler"], memoryview) else row["veriler"]
        parsed = json.loads(fernet.decrypt(data_bytes).decode("utf-8"))
    except Exception as e:
        flash(f"Veri okuma hatası: {str(e)}")
        return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))

    donem_turu = request.args.get("donem_turu", "cari")

    if tur == "bilanco":
         return render_template("tables/tablo_bilanco.html", unvan=unvan, donem=donem, vkn=vkn, aktif_list=parsed.get("aktif",[]), pasif_list=parsed.get("pasif",[]), toplamlar=parsed.get("toplamlar", {}), secilen_donem=donem_turu, donem_mapping={"cari": donem, "onceki": "Önceki Dönem"}, has_inflation=parsed.get("has_inflation", False), gorunen_kolon="cari_donem" if donem_turu=="cari" else "onceki_donem")
    elif tur == "gelir":
         gelir_list = parsed.get("tablo") or parsed.get("veriler", [])
         return render_template("tables/tablo_gelir.html", tablo=gelir_list, unvan=unvan, donem=donem, vkn=vkn, donem_mapping={"cari": donem, "onceki": "Önceki Dönem"}, secilen_donem=donem_turu, gorunen_kolon="cari_donem" if donem_turu=="cari" else "onceki_donem")
    elif tur == "kdv":
         kdv_data_raw = {r["alan"]: {"Cari": r["deger"]} for r in parsed.get("veriler", [])}
         kdv_months = ["Cari"]
         
         # --- Minimal Summary for Single View ---
         kdv_summary = {"Cari": {"matrah": 0, "hesaplanan": 0, "indirim": 0, "devreden": 0, "odenecek": 0, "iade": 0}}
         for alan, aylik in kdv_data_raw.items():
            u_alan = _u(alan)
            val = to_float_turkish(aylik.get("Cari")) or 0
            if "MATRAH TOPLAMI" in u_alan: kdv_summary["Cari"]["matrah"] = val
            elif "HESAPLANAN KDV" in u_alan or "TOPLAM KDV" in u_alan: kdv_summary["Cari"]["hesaplanan"] = val
            elif "INDIRIMLER TOPLAMI" in u_alan: kdv_summary["Cari"]["indirim"] = val
            elif "SONRAKI DONEME DEVREDEN" in u_alan: kdv_summary["Cari"]["devreden"] = val
            elif "ODENMESI GEREKEN" in u_alan: kdv_summary["Cari"]["odenecek"] = val
            elif "IADE EDILMESI GEREKEN" in u_alan: kdv_summary["Cari"]["iade"] = val

         return render_template("reports/rapor_kdv.html", 
                                secili_unvan=unvan, 
                                secili_vkn=vkn, 
                                secili_donemler=[donem], 
                                kdv_data=reorder_by_section(consolidate_kdv_rows(kdv_data_raw)), 
                                kdv_months=kdv_months,
                                kdv_summary=kdv_summary,
                                inconsistencies=[])
    
    return redirect(url_for("data.veri_giris"))
