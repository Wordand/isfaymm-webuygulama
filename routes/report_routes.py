from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, current_app
from services.db import get_conn
from services.utils import prepare_df, to_float_turkish, month_key
from services.pdf_service import (
    SECTION_KEYS,
    SECTION_ALIASES,
    canonicalize_bilanco_rows,
    canonicalize_gelir_rows,
)
from services.excel_service import (
    build_mizan_report_comparison,
    build_mizan_tax_checks,
)
from services.tax_control_service import (
    RISK_GUIDE,
    RISK_GUIDE_VERSION,
    build_data_coverage,
    build_kdv_tax_checks,
    period_sort_key,
)
from extensions import fernet
from finansal_oranlar import ORAN_DEFINITIONS, hesapla_finansal_oranlar, analiz_olustur
from auth import role_required
import pandas as pd
import json
import psycopg2.extras
import io
import math
import re
import os
import shutil
import subprocess
import tempfile
import pdfkit
from pathlib import Path
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        # Final fallback if neither is available
        ZoneInfo = None 
from urllib.parse import unquote
from collections import OrderedDict
import unicodedata

bp = Blueprint("reports", __name__)


def _calculate_available_financial_ratios(aktif_df, pasif_df, gelir_df):
    """Mevcut mali tablolara göre hesaplanabilen oranları döndürür."""
    has_balance = aktif_df is not None and pasif_df is not None
    has_income = gelir_df is not None

    if has_balance and has_income:
        return hesapla_finansal_oranlar(
            aktif_df,
            pasif_df,
            gelir_df,
            kategori="tum",
        )

    empty_df = pd.DataFrame(columns=["Kod", "Açıklama", "Cari Dönem"])

    if has_income:
        return hesapla_finansal_oranlar(
            empty_df,
            empty_df,
            gelir_df,
            kategori="karlilik",
        )

    if has_balance:
        ratios = {}
        for category in ("likidite", "yapi"):
            ratios.update(
                hesapla_finansal_oranlar(
                    aktif_df,
                    pasif_df,
                    empty_df,
                    kategori=category,
                )
            )
        return ratios

    return {}


def _required_report_types_for_category(category):
    """Finansal oran kategorisinin ihtiyaç duyduğu mali tablo türlerini döndürür."""
    if category == "karlilik":
        return {"gelir"}
    if category in {"likidite", "yapi"}:
        return {"bilanco"}
    return {"bilanco", "gelir"}


def _load_report_json(value):
    """Şifreli beyanname alanını JSON nesnesine dönüştürür.

    PostgreSQL BYTEA alanları memoryview, SQLite kayıtları bytes ve bazı eski
    kayıtlar metin olarak dönebildiği için tüm biçimler burada normalize edilir.
    """
    if value is None:
        raise ValueError("Beyanname verisi boş.")

    if isinstance(value, memoryview):
        value = value.tobytes()

    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            value = value.encode("utf-8")

    if not isinstance(value, bytes):
        raise TypeError("Beyanname verisi desteklenmeyen biçimde.")

    try:
        raw = fernet.decrypt(value)
    except Exception as decrypt_error:
        # Eski, şifrelenmeden kaydedilmiş JSON kayıtları için kontrollü uyumluluk.
        try:
            return json.loads(value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Beyanname verisinin şifresi çözülemedi.") from decrypt_error

    return json.loads(raw.decode("utf-8"))


def _load_financial_period(cursor, uid, vkn, donem, source_mode="auto"):
    """Resmi mali tabloları, eksikse mizan kaynaklı türetilen tabloları yükler."""
    cursor.execute(
        "SELECT b.tur, b.veriler FROM beyanname b "
        "JOIN mukellef m ON b.mukellef_id=m.id "
        "WHERE m.user_id=%s AND m.vergi_kimlik_no=%s AND b.donem=%s "
        "AND b.tur IN ('bilanco', 'gelir', 'mizan')",
        (uid, vkn, donem),
    )
    records = {row["tur"]: _load_report_json(row["veriler"]) for row in cursor.fetchall()}
    mizan = records.get("mizan") or {}
    mizan_summary = mizan.get("summary") or {}
    mizan_accounts = mizan.get("main_accounts") or []

    def has_account_class(prefixes):
        return any(str(row.get("code", "")).startswith(prefixes) for row in mizan_accounts)

    has_mizan_balance = mizan_summary.get("has_complete_balance")
    if has_mizan_balance is None:
        has_mizan_balance = has_account_class(("1", "2")) and has_account_class(("3", "4", "5"))

    has_mizan_income = mizan_summary.get("has_income_accounts")
    if has_mizan_income is None:
        has_mizan_income = has_account_class(("6",))

    use_official = source_mode in {"auto", "beyanname"}
    use_mizan = source_mode in {"auto", "mizan"}

    balance = records.get("bilanco") if use_official else None
    balance_source = "beyanname" if balance else None
    if use_mizan and not balance and has_mizan_balance:
        balance = {
            "aktif": mizan.get("aktif", []),
            "pasif": mizan.get("pasif", []),
            "has_inflation": False,
        }
        balance_source = "mizan"

    income = records.get("gelir") if use_official else None
    income_source = "beyanname" if income else None
    if use_mizan and not income and has_mizan_income:
        income = {"tablo": mizan.get("gelir", [])}
        income_source = "mizan"

    return balance, income, {
        "bilanco": balance_source,
        "gelir": income_source,
    }


FINANCIAL_PDF_GROUPS = OrderedDict(
    (
        (
            "Likidite",
            (
                "Cari Oran",
                "Likidite (Asit Test) Oranı",
                "Nakit Oranı",
                "Stok Bağımlılık Oranı",
            ),
        ),
        (
            "Mali Yapı",
            (
                "Yabancı Kaynak Oranı",
                "Özkaynak Oranı",
                "Borç/Özsermaye Oranı",
                "Kısa Vadeli Yabancı Kaynak Oranı",
                "Uzun Vadeli Yabancı Kaynak Oranı",
                "Yabancı Kaynaklar Vade Yapısı Oranı",
            ),
        ),
        (
            "Varlık Kullanımı",
            (
                "Alacak Devir Hızı",
                "Stok Devir Hızı",
                "Aktif Devir Hızı",
            ),
        ),
        (
            "Kârlılık",
            (
                "Brüt Kar Marjı",
                "Faaliyet Kar Marjı",
                "Olağan Kar Marjı",
                "Dönem Kar Marjı",
                "Net Kar Marjı (Satışların Karlılığı)",
                "Özsermaye Karlılığı",
                "Aktif Karlılığı",
            ),
        ),
    )
)


def _build_financial_pdf_data(cursor, uid, vkn, periods, source_mode, inflation_mode):
    """PDF raporu için mevcut finansal hesap motorundan tek veri paketi üretir."""
    reports = OrderedDict()
    source_details = OrderedDict()
    warnings = []

    for period in sorted(dict.fromkeys(periods), key=period_sort_key):
        try:
            balance, income, sources = _load_financial_period(
                cursor,
                uid,
                vkn,
                period,
                source_mode,
            )
            if not balance and not income:
                warnings.append(f"{period} için analiz edilebilir mali tablo bulunamadı.")
                continue

            active_rows = balance.get("aktif", []) if balance else []
            passive_rows = balance.get("pasif", []) if balance else []
            income_rows = income.get("tablo", []) if income else []

            inflation_column = "Cari Dönem (Enflasyonlu)"
            has_inflation_values = any(
                row.get(inflation_column) is not None
                and pd.notna(row.get(inflation_column))
                for row in active_rows + passive_rows
            )
            use_inflation = bool(
                balance
                and has_inflation_values
                and (
                    inflation_mode == "enflasyonlu"
                    or (inflation_mode == "auto" and str(period).strip() == "2023")
                )
            )
            balance_column = inflation_column if use_inflation else "Cari Dönem"
            label = f"{period} (Enf.)" if use_inflation else str(period)

            active_df = prepare_df(pd.DataFrame(active_rows), balance_column) if active_rows else None
            passive_df = prepare_df(pd.DataFrame(passive_rows), balance_column) if passive_rows else None
            income_df = prepare_df(pd.DataFrame(income_rows), "Cari Dönem") if income_rows else None
            ratios = _calculate_available_financial_ratios(active_df, passive_df, income_df)

            if not ratios:
                warnings.append(f"{period} için finansal oran hesaplanamadı.")
                continue

            reports[label] = ratios
            source_details[label] = sources
            if not balance or not income:
                missing_name = "bilanço" if not balance else "gelir tablosu"
                warnings.append(
                    f"{period} döneminde {missing_name} bulunmadığı için yalnızca mevcut verilerle hesaplama yapıldı."
                )
        except Exception as period_error:
            current_app.logger.warning(
                "PDF finansal rapor dönemi hazırlanamadı: vkn=%s donem=%s error=%s",
                vkn,
                period,
                period_error,
            )
            warnings.append(f"{period} dönemi rapora alınamadı.")

    analysis = analiz_olustur(reports) if reports else {
        "oran_analizleri": {},
        "genel_sonuc": "",
        "genel_oneriler": [],
        "gecici_donem_var": False,
    }
    period_labels = list(reports.keys())
    latest_period = period_labels[-1] if period_labels else None
    status_counts = {"safe": 0, "adequate": 0, "risky": 0}
    sections = []
    risk_items = []

    for section_name, ratio_names in FINANCIAL_PDF_GROUPS.items():
        items = []
        for ratio_name in ratio_names:
            available_periods = [
                label for label in period_labels if ratio_name in reports.get(label, {})
            ]
            if not available_periods:
                continue

            ratio_latest_period = available_periods[-1]
            ratio_info = reports[ratio_latest_period][ratio_name]
            trend_info = analysis.get("oran_analizleri", {}).get(ratio_name, {})
            level = ratio_info.get("level") or trend_info.get("seviye")
            if level in status_counts:
                status_counts[level] += 1

            advice = trend_info.get("oneri") or ratio_info.get("advice") or []
            if isinstance(advice, str):
                advice = [advice]

            period_values = [
                {
                    "period": label,
                    "value": reports.get(label, {}).get(ratio_name, {}).get("deger"),
                }
                for label in period_labels
            ]
            chart_values = []
            for index, period_value in enumerate(period_values):
                try:
                    numeric_value = float(period_value["value"])
                except (TypeError, ValueError):
                    continue
                if math.isfinite(numeric_value):
                    chart_values.append((index, numeric_value))

            sparkline_points = ""
            sparkline_markers = []
            if chart_values:
                minimum = min(value for _, value in chart_values)
                maximum = max(value for _, value in chart_values)
                span = maximum - minimum
                horizontal_span = max(len(period_values) - 1, 1)
                for index, value in chart_values:
                    x = 6 + (index / horizontal_span) * 108
                    y = 17 if span == 0 else 29 - ((value - minimum) / span) * 24
                    point = {"x": round(x, 2), "y": round(y, 2)}
                    sparkline_markers.append(point)
                sparkline_points = " ".join(
                    f'{point["x"]},{point["y"]}' for point in sparkline_markers
                )

            item = {
                "name": ratio_name,
                "formula": ratio_info.get("formula") or "-",
                "meaning": ratio_info.get("meaning") or "",
                "latest_period": ratio_latest_period,
                "latest_value": ratio_info.get("deger"),
                "level": level,
                "trend": trend_info.get("sonucu") or "Tek dönem verisi üzerinden değerlendirilmiştir.",
                "advice": advice[0] if advice else "",
                "values": period_values,
                "sparkline_points": sparkline_points,
                "sparkline_markers": sparkline_markers,
            }
            items.append(item)
            if level == "risky":
                risk_items.append(item)

        if items:
            sections.append({"name": section_name, "items": items})

    section_pages = {
        "Likidite": ("03", 5),
        "Mali Yapı": ("04", 6),
        "Varlık Kullanımı": ("05", 7),
        "Kârlılık": ("06", 8),
    }
    all_items = {
        item["name"]: item
        for section in sections
        for item in section["items"]
    }
    for section in sections:
        section_number, page_number = section_pages.get(section["name"], ("", ""))
        section["number"] = section_number
        section["page"] = page_number

    executive_metric_names = (
        "Cari Oran",
        "Borç/Özsermaye Oranı",
        "Net Kar Marjı (Satışların Karlılığı)",
        "Aktif Devir Hızı",
    )
    executive_metrics = [
        all_items[name] for name in executive_metric_names if name in all_items
    ]
    overview_metric_names = (
        "Net Kar Marjı (Satışların Karlılığı)",
        "Cari Oran",
    )
    overview_items = [
        all_items[name] for name in overview_metric_names if name in all_items
    ]

    return {
        "reports": reports,
        "analysis": analysis,
        "periods": period_labels,
        "latest_period": latest_period,
        "source_details": source_details,
        "warnings": list(dict.fromkeys(warnings)),
        "status_counts": status_counts,
        "sections": sections,
        "risk_items": risk_items,
        "executive_metrics": executive_metrics,
        "overview_items": overview_items,
        "total_indicators": sum(len(section["items"]) for section in sections),
    }


def _find_headless_browser():
    """Yerel geliştirme için Chrome/Edge yürütülebilir dosyasını bulur."""
    configured = current_app.config.get("CHROME_PATH") or os.getenv("CHROME_PATH")
    candidates = [configured]
    for command in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        candidates.append(shutil.which(command))

    for base_name, relative_path in (
        ("PROGRAMFILES", os.path.join("Google", "Chrome", "Application", "chrome.exe")),
        ("PROGRAMFILES(X86)", os.path.join("Google", "Chrome", "Application", "chrome.exe")),
        ("LOCALAPPDATA", os.path.join("Google", "Chrome", "Application", "chrome.exe")),
        ("PROGRAMFILES", os.path.join("Microsoft", "Edge", "Application", "msedge.exe")),
    ):
        base_path = os.getenv(base_name)
        if base_path:
            candidates.append(os.path.join(base_path, relative_path))

    return next((path for path in candidates if path and os.path.isfile(path)), None)


def _render_financial_pdf(html):
    """PDF'i bellekte üretir; yerel Chrome yedeğinde geçici dosyalar otomatik silinir."""
    wkhtml_path = current_app.config.get("WKHTMLTOPDF_PATH")
    if not wkhtml_path or not os.path.isfile(wkhtml_path):
        wkhtml_path = shutil.which("wkhtmltopdf")

    if wkhtml_path:
        return pdfkit.from_string(
            html,
            False,
            configuration=pdfkit.configuration(wkhtmltopdf=wkhtml_path),
            options={
                "page-size": "A4",
                "encoding": "UTF-8",
                "enable-local-file-access": "",
                "margin-top": "0mm",
                "margin-right": "0mm",
                "margin-bottom": "0mm",
                "margin-left": "0mm",
                "dpi": "96",
                "disable-smart-shrinking": "",
                "quiet": "",
            },
        )

    browser_path = _find_headless_browser()
    if not browser_path:
        raise RuntimeError("PDF oluşturma bileşeni bulunamadı.")

    with tempfile.TemporaryDirectory(prefix="isfa-financial-pdf-") as temp_dir:
        html_path = Path(temp_dir) / "report.html"
        pdf_path = Path(temp_dir) / "report.pdf"
        profile_path = Path(temp_dir) / "browser-profile"
        html_path.write_text(html, encoding="utf-8")
        result = subprocess.run(
            [
                browser_path,
                "--headless=new",
                "--disable-gpu",
                "--disable-crash-reporter",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile_path}",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if result.returncode != 0 or not pdf_path.exists():
            raise RuntimeError("Tarayıcı PDF çıktısı oluşturamadı.")
        return pdf_path.read_bytes()


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
    # Matrah Detayı: 1100, 616, 504 etc.
    if re.match(r"^(1100|616|504|113|114|115|116|117|118|119|120)\b", u) or "KAPASITE BEDELI" in u: 
        return "MATRAH DETAYI"
    
    # İndirimler Detayı: 103, 108, 109, 110, Oran Dağılımı, Devreden
    if re.match(r"^(103|108|109|110)\b", u) or "INDIRIM (%" in u or "ONCEKI DONEMDEN DEVREDEN KDV" in u or "YURTICI ALIMLARA" in u or "ITHALDE ODENEN" in u:
        return "İNDİRİMLER DETAYI"
    
    # İstisnalar: 301, 302, 325, 338, 410, 450 etc.
    if re.match(r"^(301|302|303|304|325|338|410|450)\b", u) or "TESLIM TUTARI" in u or "YUKLENILEN KDV" in u or "IADEYE KONU" in u or "TESLIM BEDELI" in u or "IADE EDILECEK" in u:
        return "İSTİSNALAR VE İADE"

    # 2. Özet Başlıklar (Sayfa 1)
    if any(x in u for x in ["TOPLAM MATRAH", "MATRAH TOPLAMI", "HESAPLANAN KDV", "ILAVESI", "TOPLAM KDV"]): return "MATRAH"
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
@role_required(allow_roles=("admin",))
def raporlama():
    vkn = request.args.get("vkn")
    fa_years = [y for y in request.args.get("fa_years", "").split(",") if y]

    unvanlar, donemler, grafik_listesi, yuklenen_dosyalar = [], [], [], []
    secili_unvan = None
    uid = session.get("user_id")

    if not uid:
        # Public visitor mode - minimal functionality or redirect to demo
        return render_template("reports/raporlama.html", 
                             mukellefler=[], 
                             donemler=[], 
                             secili_vkn=vkn, 
                             secili_unvan=None, 
                             yuklenen_dosyalar=[], 
                             grafik_listesi=[],
                             is_public=True)

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("SELECT vergi_kimlik_no, unvan FROM mukellef WHERE user_id=%s ORDER BY unvan", (uid,))
        unvanlar = [{"vkn": row["vergi_kimlik_no"], "unvan": row["unvan"]} for row in c.fetchall()]

        if vkn:
            c.execute("SELECT unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s", (vkn, uid))
            row = c.fetchone()
            if row: secili_unvan = row["unvan"]

            c.execute(
                "SELECT DISTINCT b.donem FROM beyanname b "
                "JOIN mukellef m ON b.mukellef_id=m.id "
                "WHERE m.vergi_kimlik_no=%s AND m.user_id=%s "
                "AND b.tur IN ('bilanco', 'gelir', 'mizan') "
                "ORDER BY b.donem DESC",
                (vkn, uid),
            )
            donemler = sorted(set(r["donem"] for r in c.fetchall()), reverse=True)

            c.execute(
                "SELECT b.tur, b.yuklenme_tarihi, b.donem FROM beyanname b "
                "JOIN mukellef m ON b.mukellef_id=m.id "
                "WHERE m.vergi_kimlik_no=%s AND m.user_id=%s "
                "AND b.tur IN ('bilanco', 'gelir', 'mizan') "
                "ORDER BY b.yuklenme_tarihi DESC",
                (vkn, uid),
            )
            for r in c.fetchall():
                yuklenen_dosyalar.append({"tur": r["tur"], "tarih": str(r["yuklenme_tarihi"]), "donem": r["donem"]})

    return render_template("reports/raporlama.html", mukellefler=unvanlar, donemler=donemler, secili_vkn=vkn, secili_unvan=secili_unvan, secili_fa_years=fa_years, yuklenen_dosyalar=yuklenen_dosyalar, grafik_listesi=grafik_listesi)

@bp.route("/kdv-analizi")
@role_required(allow_roles=("admin",))
def kdv_analizi():
    vkn = request.args.get("vkn")
    uid = session.get("user_id")
    mukellefler = []
    donemler = []
    secili_unvan = None
    kdv_findings = []

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute(
            "SELECT vergi_kimlik_no, unvan FROM mukellef "
            "WHERE user_id=%s ORDER BY unvan",
            (uid,),
        )
        mukellefler = [
            {"vkn": row["vergi_kimlik_no"], "unvan": row["unvan"]}
            for row in c.fetchall()
        ]

        if vkn:
            c.execute(
                "SELECT unvan FROM mukellef "
                "WHERE vergi_kimlik_no=%s AND user_id=%s",
                (vkn, uid),
            )
            row = c.fetchone()
            if row:
                secili_unvan = row["unvan"]
                c.execute(
                    "SELECT DISTINCT b.donem FROM beyanname b "
                    "JOIN mukellef m ON b.mukellef_id=m.id "
                    "WHERE m.vergi_kimlik_no=%s AND m.user_id=%s "
                    "AND b.tur='kdv'",
                    (vkn, uid),
                )
                donemler = sorted(
                    {r["donem"] for r in c.fetchall() if r["donem"]},
                    key=period_sort_key,
                    reverse=True,
                )

                c.execute(
                    "SELECT b.tur, b.donem, b.veriler FROM beyanname b "
                    "JOIN mukellef m ON b.mukellef_id=m.id "
                    "WHERE m.vergi_kimlik_no=%s AND m.user_id=%s "
                    "AND b.tur IN ('kdv', 'mizan', 'gelir')",
                    (vkn, uid),
                )
                control_records = []
                for control_row in c.fetchall():
                    try:
                        control_records.append({
                            "tur": control_row["tur"],
                            "donem": control_row["donem"],
                            "parsed": _load_report_json(control_row["veriler"]),
                        })
                    except Exception:
                        current_app.logger.warning(
                            "KDV analizinde kontrol kaydı çözümlenemedi: %s %s",
                            control_row["tur"],
                            control_row["donem"],
                        )

                kdv_records = [item for item in control_records if item["tur"] == "kdv"]
                comparison_records = [
                    item for item in control_records
                    if item["tur"] in {"mizan", "gelir"}
                ]
                kdv_findings, _, _ = build_kdv_tax_checks(
                    kdv_records,
                    other_records=comparison_records,
                    current_year=datetime.now().year,
                )
                status_order = {"warning": 0, "info": 1, "success": 2}
                kdv_findings.sort(key=lambda item: (
                    status_order.get(item.get("status"), 3),
                    item.get("category", ""),
                    period_sort_key(item.get("period", "")),
                ))

    donem_gruplari = OrderedDict()
    for donem in donemler:
        yil = str(period_sort_key(donem)[0] or "Diğer")
        donem_gruplari.setdefault(yil, []).append(donem)

    return render_template(
        "reports/kdv_analizi.html",
        mukellefler=mukellefler,
        secili_vkn=vkn,
        secili_unvan=secili_unvan,
        donemler=donemler,
        donem_gruplari=donem_gruplari,
        kdv_findings=kdv_findings,
        kdv_finding_counts={
            status: sum(1 for item in kdv_findings if item.get("status") == status)
            for status in ("warning", "info", "success")
        },
    )


@bp.route("/raporlama-grafik")
@role_required(allow_roles=("admin",))
def raporlama_grafik():
    """Trend grafiği oluşturma ve görüntüleme"""
    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan")
    donemler_str = request.args.get("donemler", "")
    donemler = sorted(dict.fromkeys(d.strip() for d in donemler_str.split(",") if d.strip()))
    
    if not vkn or not donemler:
        flash("Mükellef ve dönem seçimi gerekli.", "warning")
        return redirect(url_for("reports.raporlama"))
    
    uid = session.get("user_id")
    
    # Veri toplama
    kalem_series = {}  # {kalem_key: {year: value}}
    kalem_index = []   # [{key: ..., label: ...}]
    raporlar = {}      # {year: {oran_adi: {deger, formula, meaning, thresholds}}}
    eksik_yillar = []
    mizan_kaynakli_donemler = []
    
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            for donem in donemler:
                pb, pg, sources = _load_financial_period(c, uid, vkn, donem)

                if not pb and not pg:
                    eksik_yillar.append(donem)
                    continue

                if not pb or not pg:
                    eksik_yillar.append(donem)

                if "mizan" in sources.values():
                    mizan_kaynakli_donemler.append(donem)
                
                try:
                    # DataFrame'lere dönüştür
                    aktif_rows = pb.get("aktif", []) if pb else []
                    pasif_rows = pb.get("pasif", []) if pb else []
                    gelir_rows = pg.get("tablo", []) if pg else []
                    aktif_df = prepare_df(pd.DataFrame(aktif_rows), "Cari Dönem") if aktif_rows else None
                    pasif_df = prepare_df(pd.DataFrame(pasif_rows), "Cari Dönem") if pasif_rows else None
                    gelir_df = prepare_df(pd.DataFrame(gelir_rows), "Cari Dönem") if gelir_rows else None
                    
                    # Geçici vergi döneminde yalnızca gelir tablosu varsa kârlılık
                    # oranlarını; tam veri varsa tüm finansal oranları hesapla.
                    oranlar = _calculate_available_financial_ratios(
                        aktif_df,
                        pasif_df,
                        gelir_df,
                    )
                    if oranlar:
                        if donem not in raporlar:
                            raporlar[donem] = {}
                        raporlar[donem].update(oranlar)
                    
                    # prepare_df tüm tabloları aynı kolon adlarına dönüştürür.
                    for section_name, section_df in (
                        ("AKTİF", aktif_df),
                        ("PASİF", pasif_df),
                        ("GELİR", gelir_df),
                    ):
                        if section_df is None:
                            continue
                        for _, row in section_df.iterrows():
                            description = str(row.get("Açıklama") or "").strip()
                            if not description:
                                continue

                            code = str(row.get("Kod") or "").strip()
                            label = " ".join(part for part in (code, description) if part)
                            key = f"{section_name} - {label}"
                            value = row.get("Cari Dönem")
                            if pd.notna(value):
                                if key not in kalem_series:
                                    kalem_series[key] = {}
                                    kalem_index.append({"key": key, "label": key})
                                kalem_series[key][donem] = float(value)
                            
                except Exception as e:
                    current_app.logger.warning(
                        "Trend verisi hazirlanamadi: vkn=%s donem=%s error=%s",
                        vkn,
                        donem,
                        e,
                    )
                    eksik_yillar.append(donem)
        
        # Trend analizi oluştur
        analiz = analiz_olustur(raporlar) if raporlar else {
            "oran_analizleri": {},
            "genel_sonuc": "",
            "genel_oneriler": [],
        }
        
        return render_template(
            "reports/raporlama_grafik.html",
            vkn=vkn,
            unvan=unvan,
            donemler=donemler,
            fa_years=",".join(donemler),
            kalem_series=kalem_series,
            kalem_index=kalem_index,
            raporlar=raporlar,
            analiz=analiz,
            eksik_yillar=eksik_yillar,
            mizan_kaynakli_donemler=sorted(set(mizan_kaynakli_donemler)),
            oran_tanimlari=ORAN_DEFINITIONS,
        )
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in raporlama_grafik: {e}\n{traceback.format_exc()}")
        flash("Grafik raporu yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("reports.raporlama"))


@bp.route("/finansal-oran-raporu")
@role_required(allow_roles=("admin",))
def finansal_oran_raporu():
    vkn = request.args.get("vkn", "").strip()
    selected_periods = request.args.getlist("yillar")
    selected_periods.extend(
        period.strip()
        for period in request.args.get("donemler", "").split(",")
        if period.strip()
    )
    selected_periods = list(dict.fromkeys(selected_periods))
    source_mode = request.args.get("source_mode", "auto")
    inflation_mode = request.args.get("inflation_mode", "auto")
    if source_mode not in {"auto", "beyanname", "mizan"}:
        source_mode = "auto"
    if inflation_mode not in {"auto", "enflasyonlu", "enflasyonsuz"}:
        inflation_mode = "auto"

    if not vkn or not selected_periods:
        flash("PDF raporu için mükellef ve en az bir dönem seçilmelidir.", "warning")
        return redirect(url_for("reports.raporlama", vkn=vkn))

    uid = session.get("user_id")
    try:
        with get_conn() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT unvan FROM mukellef WHERE user_id=%s AND vergi_kimlik_no=%s",
                (uid, vkn),
            )
            taxpayer = cursor.fetchone()
            if not taxpayer:
                flash("Mükellef bulunamadı.", "danger")
                return redirect(url_for("reports.raporlama"))

            report_data = _build_financial_pdf_data(
                cursor,
                uid,
                vkn,
                selected_periods,
                source_mode,
                inflation_mode,
            )

        if not report_data["reports"]:
            flash("Seçilen dönemlerden PDF raporu oluşturacak finansal veri bulunamadı.", "warning")
            return redirect(url_for("reports.raporlama", vkn=vkn))

        generated_at = (
            datetime.now(ZoneInfo("Europe/Istanbul"))
            if ZoneInfo
            else datetime.now()
        )
        company_name = str(taxpayer["unvan"] or vkn)
        turkish_months = (
            "",
            "Ocak",
            "Şubat",
            "Mart",
            "Nisan",
            "Mayıs",
            "Haziran",
            "Temmuz",
            "Ağustos",
            "Eylül",
            "Ekim",
            "Kasım",
            "Aralık",
        )
        html = render_template(
            "reports/pdf_finansal_oran.html",
            unvan=company_name,
            vkn=vkn,
            generated_at=generated_at,
            generated_date_label=(
                f"{generated_at.day} {turkish_months[generated_at.month]} {generated_at.year}"
            ),
            source_mode=source_mode,
            inflation_mode=inflation_mode,
            **report_data,
        )
        pdf_bytes = _render_financial_pdf(html)

        ascii_name = unicodedata.normalize("NFKD", company_name).encode("ascii", "ignore").decode("ascii")
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_name).strip("_")
        filename = f"{safe_name or vkn}_finansal_analiz_raporu.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as error:
        import traceback
        current_app.logger.error(
            "Finansal PDF raporu oluşturulamadı: %s\n%s",
            error,
            traceback.format_exc(),
        )
        flash("Finansal PDF raporu oluşturulurken bir hata oluştu.", "danger")
        return redirect(url_for("reports.raporlama", vkn=vkn))


@bp.route("/rapor-kdv")
@role_required(allow_roles=("admin",))
def rapor_kdv():
    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan")
    donemler = [d for d in request.args.get("kdv_periods", "").split(",") if d]
    
    if not vkn or not donemler:
        flash("Mükellef ve dönem seçilmelidir.", "warning")
        return redirect(url_for("reports.kdv_analizi", vkn=vkn))

    kdv_data, kdv_months = {}, []
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            for donem in donemler:
                c.execute(
                    "SELECT b.veriler, b.donem FROM beyanname b "
                    "JOIN mukellef m ON m.id=b.mukellef_id "
                    "WHERE m.vergi_kimlik_no=%s AND m.user_id=%s "
                    "AND b.donem=%s AND b.tur='kdv'",
                    (vkn, session.get("user_id"), donem),
                )
                rows = c.fetchall()
                for row in rows:
                    try:
                        data_bytes = row["veriler"].tobytes() if isinstance(row["veriler"], memoryview) else row["veriler"]
                        parsed = json.loads(fernet.decrypt(data_bytes).decode("utf-8"))
                        raw_donem = parsed.get("donem") or row["donem"]
                        parts = [p.strip() for p in raw_donem.split("/") if p.strip()]
                        if len(parts) == 2:
                            ay, yil = parts[0], parts[1]
                            col = f"{yil}/{ay.upper()}"
                        else:
                            col = raw_donem
                            
                        if col not in kdv_months: kdv_months.append(col)
                        for rec in parsed.get("veriler", []):
                            kdv_data.setdefault(rec["alan"], {})[col] = rec["deger"]
                    except Exception as e: 
                        import traceback
                        current_app.logger.error(f"KDV Parse Error: {e}\n{traceback.format_exc()}")
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in rapor_kdv DB access: {e}\n{traceback.format_exc()}")
        flash("KDV raporu verileri yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("reports.kdv_analizi", vkn=vkn))

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
            if "MATRAH TOPLAMI" in u_alan or "TOPLAM MATRAH" in u_alan: kdv_summary[m]["matrah"] = val
            elif "HESAPLANAN KDV" in u_alan or "TOPLAM KDV" in u_alan: kdv_summary[m]["hesaplanan"] = val
            elif "INDIRIMLER TOPLAMI" in u_alan: kdv_summary[m]["indirim"] = val
            elif "SONRAKI DONEME DEVREDEN" in u_alan: kdv_summary[m]["devreden"] = val
            elif "ODENMESI GEREKEN" in u_alan: kdv_summary[m]["odenecek"] = val
            elif "IADE EDILMESI GEREKEN" in u_alan: kdv_summary[m]["iade"] = val
            
            # Validation Logic: Sum up specific items to check against totals
            if "(%" in u_alan and "- MATRAH" in u_alan and "INDIRIM" not in u_alan:
                calc_checks[m]["sub_matrah"] += val
            if "(%" in u_alan and "- VERGI" in u_alan and "INDIRIM" not in u_alan:
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
@role_required(allow_roles=("admin",))
def rapor_kdv_excel():
    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan", "M\u00FCkellef")
    donemler_str = request.args.get("donemler", "")
    donemler = [d for d in donemler_str.split(",") if d]

    if not vkn or not donemler:
        flash("M\u00FCkellef ve d\u00F6nem bilgisi eksik.", "warning")
        return redirect(url_for("reports.kdv_analizi", vkn=vkn))

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
                    ("   ")

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


@bp.route("/vergi-kontrolleri")
@role_required(allow_roles=("admin",))
def vergi_kontrolleri():
    uid = session.get("user_id")
    selected_vkn = (request.args.get("vkn") or "").strip()
    mukellefler = []
    selected_mukellef = None
    records = []
    decode_errors = []

    try:
        with get_conn() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT id, vergi_kimlik_no, unvan FROM mukellef "
                "WHERE user_id=%s ORDER BY unvan, vergi_kimlik_no",
                (uid,),
            )
            mukellefler = list(cursor.fetchall())

            if not selected_vkn and mukellefler:
                selected_vkn = str(mukellefler[0]["vergi_kimlik_no"])

            selected_mukellef = next(
                (
                    item for item in mukellefler
                    if str(item["vergi_kimlik_no"]) == selected_vkn
                ),
                None,
            )

            if selected_mukellef:
                cursor.execute(
                    "SELECT tur, donem, veriler, yuklenme_tarihi FROM beyanname "
                    "WHERE user_id=%s AND mukellef_id=%s "
                    "AND tur IN ('mizan', 'bilanco', 'gelir') "
                    "ORDER BY yuklenme_tarihi DESC",
                    (uid, selected_mukellef["id"]),
                )
                for row in cursor.fetchall():
                    try:
                        records.append({
                            "tur": row["tur"],
                            "donem": row["donem"],
                            "parsed": _load_report_json(row["veriler"]),
                            "yuklenme_tarihi": row.get("yuklenme_tarihi"),
                        })
                    except Exception:
                        decode_errors.append(f"{row['donem']} {row['tur']}")
    except Exception as error:
        import traceback
        current_app.logger.error(
            "Error in vergi_kontrolleri data load: %s\n%s",
            error,
            traceback.format_exc(),
        )
        flash("Vergi kontrolleri verileri yüklenirken bir hata oluştu.", "danger")

    coverage = [
        item for item in build_data_coverage(records)
        if item["key"] != "kdv"
    ]
    findings = []

    mizan_records = sorted(
        (record for record in records if record["tur"] == "mizan"),
        key=lambda record: period_sort_key(record["donem"]),
        reverse=True,
    )
    for record in mizan_records:
        parsed = record["parsed"]
        for item in parsed.get("validation", []):
            if item.get("status") != "warning":
                continue
            findings.append({
                "category": "Mizan doğrulama",
                "title": item.get("title") or "Mizan doğrulama farkı",
                "status": "warning",
                "classification": "Matematiksel uyumsuzluk",
                "detail": item.get("detail") or "Mizan doğrulamasında fark bulundu.",
                "period": record["donem"],
                "source": "Mizan",
                "action": "Kaynak mizanı, dönem sonu kayıtlarını ve PDF/Excel ayrıştırmasını kontrol edin.",
            })

        for item in build_mizan_tax_checks(
            parsed.get("raw_rows", []),
            parsed.get("main_accounts", []),
        ):
            finding = dict(item)
            finding.update({
                "period": record["donem"],
                "source": "Mizan",
                "classification": (
                    "Risk sinyali" if item.get("status") == "warning"
                    else "Ek belge/veri gerekli" if item.get("status") == "info"
                    else "Otomatik kontrol"
                ),
            })
            findings.append(finding)

    if decode_errors:
        findings.insert(0, {
            "category": "Veri kalitesi",
            "title": "Okunamayan kayıtlar var",
            "status": "warning",
            "classification": "Veri kalitesi",
            "detail": f"{len(decode_errors)} kayıt çözümlenemedi: {', '.join(decode_errors[:5])}.",
            "source": "Yüklenen dosyalar",
            "action": "İlgili belgelerin güncel ve okunabilir kopyalarını yeniden yükleyin.",
        })

    status_order = {"warning": 0, "info": 1, "success": 2}
    findings.sort(key=lambda item: (
        status_order.get(item.get("status"), 3),
        item.get("category", ""),
        period_sort_key(item.get("period", "")),
    ))
    finding_counts = {
        status: sum(1 for item in findings if item.get("status") == status)
        for status in ("warning", "info", "success")
    }

    return render_template(
        "reports/vergi_kontrolleri.html",
        mukellefler=mukellefler,
        selected_vkn=selected_vkn,
        selected_mukellef=selected_mukellef,
        coverage=coverage,
        findings=findings,
        finding_counts=finding_counts,
        risk_guide=[
            item for item in RISK_GUIDE
            if item.get("category") != "KDV kontrolleri"
            and "KDV" not in item.get("title", "")
        ],
        risk_guide_version=RISK_GUIDE_VERSION,
    )

@bp.route("/tablo-mizan/<string:tur>")
@role_required(allow_roles=("admin",))
def tablo_mizan(tur):
    vkn = request.args.get("vkn")
    donem = request.args.get("donem")
    if not (tur and vkn and donem):
        flash("Eksik parametre.")
        return redirect(url_for("data.veri_giris"))

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute(
                "SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=%s AND user_id=%s",
                (vkn, session["user_id"]),
            )
            row = c.fetchone()
            if not row:
                 flash("Mükellef bulunamadı.")
                 return redirect(url_for("data.veri_giris"))
            mid, unvan = row["id"], row["unvan"]
            c.execute("SELECT veriler FROM beyanname WHERE user_id=%s AND mukellef_id=%s AND donem=%s AND tur='mizan'", (session["user_id"], mid, donem))
            mizan_row = c.fetchone()
            official_reports = {}
            if tur == "kontroller":
                c.execute(
                    "SELECT tur, veriler FROM beyanname "
                    "WHERE user_id=%s AND mukellef_id=%s AND donem=%s "
                    "AND tur IN ('bilanco', 'gelir')",
                    (session["user_id"], mid, donem),
                )
                official_reports = {
                    official_row["tur"]: _load_report_json(official_row["veriler"])
                    for official_row in c.fetchall()
                }
            
        if not mizan_row:
            flash("Mizan verisi bulunamadı.")
            return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))

        mizan_data = _load_report_json(mizan_row["veriler"])

        if tur == "bilanco":
             summary = mizan_data.get("summary") or {}
             toplamlar = {
                 "AKTİF": {"cari": summary.get("active_total", 0)},
                 "PASİF": {"cari": summary.get("passive_total", 0)},
             }
             return render_template(
                 "tables/tablo_bilanco.html",
                 page_title="Mizandan Oluşturulan Bilanço",
                 unvan=unvan,
                 donem=donem,
                 vkn=vkn,
                 aktif_list=canonicalize_bilanco_rows(mizan_data.get("aktif", []), "AKTİF"),
                 pasif_list=canonicalize_bilanco_rows(mizan_data.get("pasif", []), "PASİF"),
                 toplamlar=toplamlar,
                 secilen_donem="cari",
                 donem_mapping={"cari": donem},
                 has_inflation=False,
                 gorunen_kolon="Cari Dönem",
                 aktif_alt_toplamlar={},
                 pasif_alt_toplamlar={},
             )
        elif tur == "gelir":
             return render_template(
                 "tables/tablo_gelir.html",
                 page_title="Mizandan Oluşturulan Gelir Tablosu",
                 tablo=canonicalize_gelir_rows(mizan_data.get("gelir", [])),
                 unvan=unvan,
                 donem=donem,
                 vkn=vkn,
                 donem_mapping={"cari": donem},
                 secilen_donem="cari",
                 has_inflation=False,
                 gorunen_kolon="cari_donem",
             )
        elif tur == "kontroller":
             validation = mizan_data.get("validation", [])
             tax_checks = build_mizan_tax_checks(
                 mizan_data.get("raw_rows", []),
                 mizan_data.get("main_accounts", []),
             )
             comparison = build_mizan_report_comparison(official_reports, mizan_data)
             summary = dict(mizan_data.get("summary", {}))
             summary["tax_check_count"] = len(tax_checks)
             summary["warning_count"] = sum(
                 1 for item in validation + tax_checks
                 if item.get("status") == "warning"
             )
             return render_template(
                 "tables/tablo_mizan_kontroller.html",
                 unvan=unvan,
                 donem=donem,
                 vkn=vkn,
                 summary=summary,
                 validation=validation,
                 tax_checks=tax_checks,
                 comparison=comparison,
                 official_types=sorted(official_reports.keys()),
             )
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in tablo_mizan: {e}\n{traceback.format_exc()}")
        flash("Mizan tablosu yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("data.veri_giris", vkn=vkn, donem=donem))
    
    return redirect(url_for("data.veri_giris"))

@bp.route("/finansal-analiz")
@role_required(allow_roles=("admin",))
def finansal_analiz():
    secili_vkn = request.args.get("vkn")
    secili_yillar = request.args.getlist("yillar") or []
    inflation_mode = request.args.get("inflation_mode", "auto")
    kategori = request.args.get("kategori", "likidite")
    source_mode = request.args.get("source_mode", "auto")
    if source_mode not in {"auto", "beyanname", "mizan"}:
        source_mode = "auto"
    
    uid = session.get("user_id")
    unvanlar, mevcut_yillar, trend_data, oran_detaylari = [], [], {}, {}
    source_details = OrderedDict()
    display_periods = []
    is_guest = not uid
    
    uyarilar = []
    try:
        if not uid:
            # Ziyaretçi modu — DB sorgusu yapma
            pass
        else:
            with get_conn() as conn:
                c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                c.execute(
                    "SELECT vergi_kimlik_no, unvan FROM mukellef "
                    "WHERE user_id=%s ORDER BY unvan",
                    (uid,),
                )
                unvanlar = [
                    {"vkn": r["vergi_kimlik_no"], "unvan": r["unvan"]}
                    for r in c.fetchall()
                ]

                if secili_vkn:
                    c.execute(
                        "SELECT b.donem, b.tur FROM beyanname b "
                        "JOIN mukellef m ON b.mukellef_id=m.id "
                        "WHERE m.user_id=%s AND m.vergi_kimlik_no=%s "
                        "AND b.tur IN ('bilanco', 'gelir', 'mizan')",
                        (uid, secili_vkn),
                    )
                    existing_docs = c.fetchall()

                    docs_by_year = {}
                    for row in existing_docs:
                        clean_donem = str(row["donem"]).strip()
                        if row["tur"] == "mizan":
                            if source_mode not in {"auto", "mizan"}:
                                continue
                            docs_by_year.setdefault(clean_donem, set()).update({"bilanco", "gelir", "mizan"})
                        else:
                            if source_mode not in {"auto", "beyanname"}:
                                continue
                            report_types = docs_by_year.setdefault(clean_donem, set())
                            report_types.update({row["tur"], f"official_{row['tur']}"})

                    mevcut_yillar = sorted(docs_by_year.keys(), reverse=True)
                    if not secili_yillar:
                        secili_yillar = mevcut_yillar.copy()

                    process_queue = []
                    required_types = _required_report_types_for_category(kategori)
                    secili_yillar_sorted = sorted(
                        dict.fromkeys(str(y).strip() for y in secili_yillar if str(y).strip()),
                        reverse=True,
                    )

                    for y_str in secili_yillar_sorted:
                        match_donem = next(
                            (
                                d for d, turler in docs_by_year.items()
                                if (d == y_str or d.startswith(y_str + "/"))
                                and required_types.issubset(turler)
                            ),
                            None,
                        )
                        if not match_donem:
                            gerekli_tablo = {
                                frozenset({"gelir"}): "gelir tablosu",
                                frozenset({"bilanco"}): "bilanço",
                            }.get(frozenset(required_types), "bilanço ve gelir tablosu")
                            uyarilar.append(f"{y_str} için gerekli {gerekli_tablo} bulunamadı.")
                            continue

                        matched_types = docs_by_year.get(match_donem, set())
                        has_official_balance = "official_bilanco" in matched_types
                        if inflation_mode == "auto" and y_str == "2023" and has_official_balance:
                            process_queue.append({"label": "2023 (Enf)", "db_donem": match_donem, "mode": "enflasyonlu"})
                        elif inflation_mode == "enflasyonlu":
                            process_queue.append({"label": y_str, "db_donem": match_donem, "mode": "enflasyonlu"})
                        else:
                            process_queue.append({"label": y_str, "db_donem": match_donem, "mode": "normal"})

                    process_queue = sorted(process_queue, key=lambda item: item["label"])
                    display_periods = []

                    for item in process_queue:
                        label = item["label"]
                        db_donem = item["db_donem"]
                        mode = item["mode"]

                        try:
                            pb, pg, sources = _load_financial_period(
                                c,
                                uid,
                                secili_vkn,
                                db_donem,
                                source_mode,
                            )

                            available_types = {
                                report_type for report_type, payload
                                in (("bilanco", pb), ("gelir", pg)) if payload
                            }
                            if not required_types.issubset(available_types):
                                uyarilar.append(f"{label} için seçilen oran grubuna ait gerekli tablolar bulunamadı.")
                                continue

                            if "mizan" in sources.values():
                                source_note = f"{label} döneminde eksik resmi mali tablo yerine mizan kaynaklı tablo kullanıldı."
                                if source_note not in uyarilar:
                                    uyarilar.append(source_note)

                            source_details[label] = sources

                            aktif_rows = pb.get("aktif", []) if pb else []
                            pasif_rows = pb.get("pasif", []) if pb else []
                            inflation_column = "Cari Dönem (Enflasyonlu)"
                            has_inflation_values = any(
                                row.get(inflation_column) is not None
                                and pd.notna(row.get(inflation_column))
                                for row in aktif_rows + pasif_rows
                            )

                            if mode == "enflasyonlu" and pb and not has_inflation_values:
                                uyarilar.append(
                                    f"{label} için enflasyon düzeltmesi sonrası bilanço verisi bulunamadı."
                                )
                                continue

                            t_col = inflation_column if mode == "enflasyonlu" else "Cari Dönem"

                            empty_df = pd.DataFrame(columns=["Kod", "Açıklama", "Cari Dönem"])
                            aktif_df = prepare_df(pd.DataFrame(aktif_rows), t_col) if aktif_rows else empty_df
                            pasif_df = prepare_df(pd.DataFrame(pasif_rows), t_col) if pasif_rows else empty_df
                            gelir_rows = pg.get("tablo", []) if pg else []
                            gelir_df = prepare_df(pd.DataFrame(gelir_rows), "Cari Dönem") if gelir_rows else empty_df

                            if kategori == "karlilik" and pg and not pb:
                                uyarilar.append(
                                    f"{label} için bilanço bulunmadığından aktif ve özsermaye kârlılığı hesaplanmadı."
                                )
                            calc_res = hesapla_finansal_oranlar(
                                aktif_df,
                                pasif_df,
                                gelir_df,
                                kategori,
                            )

                            for key, result in calc_res.items():
                                value = result.get("deger") if isinstance(result, dict) else result
                                trend_data.setdefault(key, {})[label] = (
                                    float(value) if value is not None and pd.notna(value) else None
                                )
                                if isinstance(result, dict) and key not in oran_detaylari:
                                    oran_detaylari[key] = {
                                        "formula": result.get("formula"),
                                        "meaning": result.get("meaning"),
                                        "thresholds": result.get("thresholds"),
                                        "direction": result.get("direction", "higher"),
                                        "advice": result.get("advice"),
                                    }
                            if label not in display_periods:
                                display_periods.append(label)
                        except Exception as item_error:
                            current_app.logger.warning(
                                "Finansal analiz verisi hazirlanamadi: vkn=%s donem=%s error=%s",
                                secili_vkn,
                                db_donem,
                                item_error,
                            )
                            uyarilar.append(f"{label} dönemi analiz edilemedi.")

    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in finansal_analiz: {e}\n{traceback.format_exc()}")
        flash("Finansal analiz sayfası yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("main.home"))

    return render_template("reports/finansal_analiz.html", 
                           unvanlar=unvanlar, 
                           secili_vkn=secili_vkn, 
                           kategori=kategori, 
                           mevcut_yillar=mevcut_yillar, 
                           secili_yillar=secili_yillar, 
                           display_periods=display_periods,
                           inflation_mode=inflation_mode, 
                           source_mode=source_mode,
                           trend_data=trend_data, 
                           oran_detaylari=oran_detaylari,
                           oran_tanimlari=ORAN_DEFINITIONS,
                           source_details=source_details,
                           uyarilar=uyarilar,
                           is_guest=is_guest)

@bp.route("/pdf-belgeler-tablo")
@role_required(allow_roles=("admin",))
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

    if tur in ["bilanco", "bilanco_enf"]:
         # Enflasyonlu belge zaten enflasyon verisini 'Cari Dönem' olarak içerdiği için 
         # tekrar enflasyon toggle'ına gerek yok ama dropdown'da gösterelim
         override_inflation = False if tur == "bilanco_enf" else parsed.get("has_inflation", False)
         
         # Check if previous period data actually exists
         has_prev_data = any(
             row.get("Önceki Dönem") is not None 
             for row in parsed.get("aktif", []) + parsed.get("pasif", [])
         )
         
         # Build donem_mapping dynamically
         donem_mapping = {"cari": donem}
         if has_prev_data:
             donem_mapping["onceki"] = str(int(donem)-1) if donem and donem.isdigit() else "Önceki Dönem"
         
         # For bilanco_enf, label the cari option as "Enflasyonlu" since that's what the data is
         if tur == "bilanco_enf":
             donem_mapping["cari"] = f"{donem} Enflasyonlu"
         elif override_inflation:
             donem_mapping["cari_enflasyon"] = f"{donem} Enflasyonlu"
         
         return render_template("tables/tablo_bilanco.html", 
                                page_title="ENFLASYONLU BİLANÇO" if tur=="bilanco_enf" else "Bilanço Tablosu",
                                unvan=unvan, 
                                donem=donem, 
                                vkn=vkn, 
                                aktif_list=canonicalize_bilanco_rows(parsed.get("aktif", []), "AKTİF"),
                                pasif_list=canonicalize_bilanco_rows(parsed.get("pasif", []), "PASİF"),
                                toplamlar=parsed.get("toplamlar", {}), 
                                secilen_donem=donem_turu, 
                                donem_mapping=donem_mapping, 
                                has_inflation=True if tur == "bilanco_enf" else override_inflation, 
                                gorunen_kolon="Cari Dönem" if donem_turu=="cari" else ("Cari Dönem (Enflasyonlu)" if donem_turu=="cari_enflasyon" else "Önceki Dönem"))
    elif tur in ["gelir", "gelir_enf"]:
         # Gelir tablosu için de benzer mantık
         override_inflation = False if tur == "gelir_enf" else parsed.get("has_inflation", False)
         gelir_list = canonicalize_gelir_rows(
             parsed.get("tablo") or parsed.get("veriler", [])
         )
         
         # Check if previous period data actually exists
         has_prev_data = any(
             row.get("onceki_donem") is not None 
             for row in gelir_list
         )
         
         # Build donem_mapping dynamically
         donem_mapping = {"cari": donem}
         if has_prev_data:
             donem_mapping["onceki"] = str(int(donem)-1) if donem and donem.isdigit() else "Önceki Dönem"
         if override_inflation:
             donem_mapping["cari_enflasyon"] = f"{donem} Enflasyonlu"
         
         return render_template("tables/tablo_gelir.html", 
                                page_title="ENFLASYONLU GELİR TABLOSU" if tur=="gelir_enf" else "Gelir Tablosu",
                                tablo=gelir_list, 
                                unvan=unvan, 
                                donem=donem, 
                                vkn=vkn, 
                                donem_mapping=donem_mapping, 
                                secilen_donem=donem_turu, 
                                has_inflation=override_inflation,
                                gorunen_kolon="cari_donem" if donem_turu=="cari" else ("cari_donem_enflasyonlu" if donem_turu=="cari_enflasyon" else "onceki_donem"))
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
