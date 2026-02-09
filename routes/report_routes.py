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

CANON_SECTIONS = [
    "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "KISMİ TEVKİFAT UYGULANAN İŞLEMLER",
    "DİĞER İŞLEMLER",
    "MATRAH TOPLAMI",
    "İNDİRİMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV",
    "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM",
    "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER",
    "DİĞER İADE HAKKI DOĞURAN İŞLEMLER",
    "SONUÇ",
    "DİĞER BİLGİLER",
]

def _u(s):
    return (s or "").upper().replace("İ","I").replace("Ş","S").replace("Ğ","G").replace("Ü","U").replace("Ö","O").replace("Ç","C")

def classify_section(key: str) -> str:
    u = _u(key).strip()
    if key.startswith("§ "): return key[2:].strip()
    if u.startswith("TEVKIFATSIZ"): return "TEVKİFAT UYGULANMAYAN İŞLEMLER"
    if "KDVGUT" in u or "I/C-" in u or "KDV ORANI" in u or "TEVKIFAT ORANI" in u or "DIGER HIZMETLER" in u:
        return "KISMİ TEVKİFAT UYGULANAN İŞLEMLER"
    if u.startswith("MATRAH TOPLAMI") or u in {_u("Hesaplanan KDV"), _u("Toplam KDV")}: return "MATRAH TOPLAMI"
    if "IADE EDILECEK KDV" in u or "IADE EDILMESI GEREKEN" in u: return "SONUÇ"
    if "INDIRIMLER TOPLAMI" in u or "ONCEKI DONEMDEN DEVREDEN" in u or "YURTICI ALIM KDV" in u: return "İNDİRİMLER"
    if re.match(r"^\d{1,2}\s*-\s*(MATR|VERGI)", u) or "BU DONEME AIT INDIRILECEK KDV TOPLAMI" in u: return "BU DÖNEME AİT İNDİRİLECEK KDV"
    if u.startswith("IHRAC") or "IHRACATIN" in u: return "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM"
    if "TESLIM VE HIZMET TUTARI" in u or "YUKLENILEN KDV" in u: return "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER"
    if u.endswith("IADEYE KONU OLAN KDV") or u.endswith("TESLIM BEDELI"): return "DİĞER İADE HAKKI DOĞURAN İŞLEMLER"
    if "SONRAKI DONEME DEVREDEN" in u or u.startswith("TECIL EDILECEK") or u.startswith("BU DONEMDE ODENMESI"): return "SONUÇ"
    if u.startswith("TESLIM VE HIZMETLERIN KARSILIGINI"): return "DİĞER BİLGİLER"
    return "DİĞER İŞLEMLER"

def normalize_row_key(key: str) -> str:
    if key.startswith("§ "): return key
    u = _u(key)
    if "ALINAN MALLARIN IADESI" in u: return "Alınan Malların İadesi - " + ("Matrah" if "MATR" in u else "Vergi")
    if ("AMORTIS" in u or "SABIT KIYMET" in u or "MAKINE" in u): return "Amortis mana Tabi Sabit Kıymet - " + ("Matrah" if "MATR" in u else "Vergi")
    if "DIGER HIZMETLER" in u:
        suffix = "Matrah"
        if "KDV ORANI" in u: suffix = "KDV Oranı"
        elif "TEVKIFAT ORANI" in u: suffix = "Tevkifat Oranı"
        elif "VERG" in u: suffix = "Vergi"
        return f"Diğer Hizmetler - {suffix}"
    return key

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
    buckets = {sec: [] for sec in CANON_SECTIONS}
    orphans = []
    for key in kdv_data:
        if key.startswith("§ "): continue
        sec = classify_section(key)
        if sec in buckets: buckets[sec].append(key)
        else: orphans.append(key)
    out = OrderedDict()
    for sec in CANON_SECTIONS:
        hdr = f"§ {sec}"
        if buckets.get(sec) or hdr in kdv_data:
            out[hdr] = kdv_data.get(hdr, {})
            for r in buckets.get(sec, []): out[r] = kdv_data[r]
    for r in orphans: out[r] = kdv_data[r]
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
    kdv_data = reorder_by_section(consolidate_kdv_rows(kdv_data))
    
    return render_template("reports/rapor_kdv.html", secili_unvan=unvan, secili_vkn=vkn, secili_donemler=donemler, kdv_data=kdv_data, kdv_months=kdv_months)

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
         return render_template("reports/rapor_kdv.html", secili_unvan=unvan, secili_vkn=vkn, secili_donemler=[donem], kdv_data=reorder_by_section(consolidate_kdv_rows({r["alan"]: {"Cari": r["deger"]} for r in parsed.get("veriler", [])})), kdv_months=["Cari"])
    
    return redirect(url_for("data.veri_giris"))
