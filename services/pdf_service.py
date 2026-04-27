import re
import pandas as pd
import pdfplumber
import difflib
import unicodedata
import json
from .utils import to_float_turkish
from hesaplar import BILANCO_HESAPLARI
from gelir import GELIR_TABLOSU_HESAPLARI

NEGATIVE_BILANCO_CODES = set([
    '103', '119', '122', '124', '129', '137', '139', '158',
    '199', '222', '224', '229', '237', '239', '241', '243',
    '244', '246', '247', '249', '257', '268', '278', '298',
    '299', '302', '308', '322', '337', '371', '402', '408',
    '422', '437', '501', '503', '580', '591'
])

NEGATIVE_GELIR_CODES = set([
    '610', '611', '612', '620', '621', '622', '623', '630',
    '631', '632', '653', '654', '655', '656', '657', '658',
    '659', '660', '661', '680', '681', '689', '690'
])

num_val_pattern_str = r"[-+]?(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d{2})?(?:\s*\([^\)]*\)|\s*-\s*)?"
find_all_nums_in_line = re.compile(num_val_pattern_str)
AMT_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")
FIND_NUM = re.compile(r"\d{1,3}(?:[\.\s]\d{3})*(?:,\d{2})?")

SECTION_KEYS = [
    "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "KISMİ TEVKİFAT UYGULANAN İŞLEMLER",
    "DİĞER İŞLEMLER",
    "İNDİRİMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV",
    "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM",
    "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER",
    "DİĞER İADE HAKKI DOĞURAN İŞLEMLER",
    "DİĞER BİLGİLER",
]

SECTION_ALIASES = {
    "DİĞER İŞLEMELER": "DİĞER İŞLEMLER",
    "TEVKİFAT UYGULANMAYAN İŞLEMELER": "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "İNDİRİMİNLEDRİRİMLER": "İNDİRİMLER",
    "DİĞER İŞLİENMDLİRERİMLER": "DİĞER İŞLEMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV TUTARININ ORANLARA GÖRE DAĞILIMI": "BU DÖNEME AİT İNDİRİLECEK KDV",
}

SUMMARY_REDIRECT = {
    "Hesaplanan Katma Değer Vergisi": "Hesaplanan KDV",
    "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi": "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi",
    "Toplam Katma Değer Vergisi": "Toplam KDV",
}


def extract_mukellef_bilgileri(text: str):
    unvan = "Bilinmiyor"
    donem = "Bilinmiyor"
    vkn   = "Bilinmiyor"
    tur   = "Bilinmiyor"

    # Normalize text for better matching
    text_norm = _stripped_canon(text)

    # --- Tür ---
    # --- Tür ---
    if "KURUMLAR" in text_norm and ("VERG" in text_norm or "BEYANNAME" in text_norm):
        tur = "Kurumlar"
        if "BILANCO" in text_norm or "BILAN.O" in text_norm:
            tur = "Bilanço"
        elif "GELIR" in text_norm and "TABLO" in text_norm:
            tur = "Gelir Tablosu"
    elif "KATMA" in text_norm and ("VERG" in text_norm or "BEYANNAME" in text_norm):
        tur = "KDV"
    
    # Debug log (will show in terminal)
    print(f"DEBUG: File processed. Type detected: {tur}")

    # --- VKN ---
    m_vkn = re.search(r"(?:Vergi Kimlik|Kimlik|T\.C\.\s*Kimlik)\s*(?:No|Numarası)[\s:]*(\d{10,11})", text, re.I)
    if not m_vkn:
        m_vkn = re.search(r"(?:VKN|TCCK)\s*[:\s]*(\d{10,11})", text_norm)
    
    if m_vkn:
        vkn = m_vkn.group(1).strip()

    # --- Unvan ---
    # PDF format: "Soyadı (Unvanı) AKONA PLASTİK ZİR GID İNŞ"
    #             "Adı (Unvanın Devamı) SAN VE TİC LTD"
    lines = text.split("\n")
    unvan_parts = []
    
    for i, line in enumerate(lines):
        line_s = line.strip()
        # Pattern 1: "Soyadı (Unvanı) COMPANY NAME" or "Soyadı/Ünvanı COMPANY NAME"
        m1 = re.match(r"(?:Soyad[ıi]\s*(?:\(Unvan[ıi]\)|/\s*[ÜU]nvan[ıi]))\s+(.*)", line_s, re.I)
        if m1:
            part = m1.group(1).strip()
            if part and not re.match(r"^Soyad", part, re.I):
                unvan_parts = [part]
                # Check next line for continuation
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    m2 = re.match(r"(?:Ad[ıi]\s*(?:\(Unvan[ıi]n\s*Devam[ıi]\)|/\s*[ÜU]nvan))\s+(.*)", next_line, re.I)
                    if m2:
                        cont = m2.group(1).strip()
                        if cont:
                            unvan_parts.append(cont)
                break
    
    if unvan_parts:
        unvan = " ".join(unvan_parts).upper()
    else:
        # Fallback: original regex approach
        m_unvan = re.search(r"(?:Adı\s*Soyadı/Ünvanı|Soyadı/Ünvanı|Unvanı)[\s\):]*\n?\s*([^\n\d]+)", text, re.I)
        if m_unvan:
            unvan = m_unvan.group(1).strip().upper()
    
    # Clean up any label artifacts from the unvan
    for label in ["(UNVANI)", "(UNVANIN DEVAMI)", "SOYADI/ÜNVANI", "SOYADI/UNVANI", 
                   "ADI SOYADI/UNVANI", "ADI SOYADI/ÜNVANI", "E-POSTA ADRESI", "TELEFON NO",
                   "SOYADI,", "ADI", "SOYADI"]:
        unvan = re.sub(re.escape(label), "", unvan, flags=re.I).strip()
    unvan = re.sub(r"^\(.*?\)\s*", "", unvan)  # Remove leading parenthetical like "(Unvanı)"
    unvan = re.sub(r"\s+", " ", unvan).strip(": ").strip()

    # --- Dönem ---
    # Pattern 1: Yıl: 2025 Ay: Aralık
    m_yil = re.search(r"\b(?:Yıl|Yil|YIL)\b[:\s]*(\d{4})", text, re.I)
    m_ay = re.search(r"\b(?:Ay|AY)\b[:\s]*([^\s\d:]+)", text, re.I)
    
    # Additional month names for matching
    all_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    month_map = {
        "ARALK": "Aralık", "ARALIK": "Aralık", "OCAK": "Ocak", "SUBAT": "Şubat", "ŞUBAT": "Şubat", 
        "MART": "Mart", "NISAN": "Nisan", "NİSAN": "Nisan", "MAYIS": "Mayıs", "HAZIRAN": "Haziran", 
        "HAZİRAN": "Haziran", "TEMMUZ": "Temmuz", "AGUSTOS": "Ağustos", "AĞUSTOS": "Ağustos", 
        "EYLUL": "Eylül", "EYLÜL": "Eylül", "EKIM": "Ekim", "EKİM": "Ekim", "KASIM": "Kasım"
    }
    
    if m_yil and m_ay:
        ay_str = m_ay.group(1).strip()
        ay_norm = _stripped_canon(ay_str)
        ay_clean = month_map.get(ay_norm, ay_str.capitalize())
        donem = f"{ay_clean} / {m_yil.group(1)}"
    else:
        # Pattern 2: Dönem: Aralık 2024 / Vergilendirme Dönemi: Aralık 2024
        m_donem_text = re.search(r"(?:Dönem|Vergilendirme\s*Dönemi)[:\s]*([A-Za-zÇĞİÖŞÜçğıöşü]+)\s*[/\-\s]*(\d{4})", text, re.I)
        if m_donem_text:
            ay_str = m_donem_text.group(1).strip()
            ay_norm = _stripped_canon(ay_str)
            ay_clean = month_map.get(ay_norm, ay_str.capitalize())
            donem = f"{ay_clean} / {m_donem_text.group(2)}"
        else:
            # Pattern 3: 12/2024 or 12 / 2024
            m_num = re.search(r"(\d{2})\s*/\s*(\d{4})", text)
            if m_num:
                donem = f"{m_num.group(1)} / {m_num.group(2)}"
            # Pattern 4: Direct month name + year in text (e.g. "Aralık 2024")
            elif not m_yil:
                month_pattern = "|".join(all_months)
                m_direct = re.search(rf"({month_pattern})\s*[/\-\s]*(\d{{4}})", text, re.I)
                if m_direct:
                    ay_str = m_direct.group(1).strip()
                    ay_norm = _stripped_canon(ay_str)
                    ay_clean = month_map.get(ay_norm, ay_str.capitalize())
                    donem = f"{ay_clean} / {m_direct.group(2)}"
            elif m_yil:
                donem = m_yil.group(1)

    return {
        "unvan": unvan,
        "donem": donem,
        "vergi_kimlik_no": vkn,
        "tur": tur
    }

def find_account_code(block_name, description, parent_group=None):
    original_description = description.strip()
    kod_match = re.match(r"^\s*(\d{1,3})\s*[.\-]?\s*(.*)", original_description)

    if kod_match:
        return kod_match.group(1)

    if re.match(r"^\s*([A-ZÇĞİÖŞÜ]|[IVXLCDM]+)\.\s*[\w\s\-()]+$", original_description):
        return ""

    description_clean = re.sub(r"^\s*[\.\s]+", "", original_description)
    description_clean = re.sub(r"[^\w\s]", "", description_clean.lower().strip())

    best_match = ""
    best_score = 0
    ana_blok = BILANCO_HESAPLARI.get(block_name.upper(), {})

    for grup, alt_gruplar in ana_blok.items():
        if parent_group and parent_group.strip().lower() != grup.strip().lower():
            continue

        for alt_grup, kod_dict in alt_gruplar.items():
            for kod, tanim in kod_dict.items():
                tanim_clean = tanim.lower().strip()
                tanim_clean_simple = re.sub(r"^\d+\.\s*", "", tanim_clean)
                tanim_clean_simple = re.sub(r"[^\w\s]", "", tanim_clean_simple)

                if description_clean == tanim_clean_simple or description_clean in tanim_clean_simple:
                    return kod

                if abs(len(tanim_clean_simple) - len(description_clean)) > 30:
                    continue

                score = difflib.SequenceMatcher(None, description_clean, tanim_clean_simple).ratio()
                if score > best_score and score > 0.65:
                    best_match = kod
                    best_score = score
    return best_match

def parse_numeric_columns(line_stripped):
    numeric_values = re.findall(r"\d[\d\.\,]*", line_stripped)
    numeric_values = [v for v in numeric_values if v.strip()]

    onceki = cari = cari_enflasyon = None
    if len(numeric_values) >= 3:
        onceki = to_float_turkish(numeric_values[-3])
        cari = to_float_turkish(numeric_values[-2])
        cari_enflasyon = to_float_turkish(numeric_values[-1])
    elif len(numeric_values) == 2:
        onceki = to_float_turkish(numeric_values[0])
        cari = to_float_turkish(numeric_values[1])
    elif len(numeric_values) == 1:
        cari = to_float_turkish(numeric_values[0])

    desc_clean = re.sub(r"\d[\d\.\,]*", "", line_stripped)
    desc_clean = re.sub(r"\s{2,}", " ", desc_clean) 
    desc_clean = re.sub(r"[\.]+(?=\s|$)", ".", desc_clean) 
    description = desc_clean.strip(" .-•").strip()

    return description, onceki, cari, cari_enflasyon

def parse_table_block(text: str, block_name: str = "AKTİF", debug: bool = True):
    header_pattern = (
        rf"{block_name}[\s\S]*?Açıklama.*?(?:\n.*?Cari Dönem)?[\s\S]*?\(\d{{4}}\).*?\(\d{{4}}\)"
    )
    end_pattern = rf"(?i)\n\s*{block_name}\s*TOPLAMI"

    block_start_match = re.search(header_pattern, text, re.DOTALL | re.IGNORECASE)
    if not block_start_match:
        return pd.DataFrame(columns=["Kod", "Açıklama", "Önceki Dönem", "Cari Dönem"]), False

    header_line_text_full_match = block_start_match.group(0)
    has_inflation_column_from_header = bool(
        re.search(r"enflasyon", header_line_text_full_match, re.IGNORECASE)
    )

    content_after_start = text[block_start_match.end():]
    block_end_match = re.search(end_pattern, content_after_start, re.DOTALL | re.IGNORECASE)
    block_content = (
        content_after_start[:block_end_match.start()].strip()
        if block_end_match
        else content_after_start.strip()
    )

    lines = block_content.split("\n")
    data = []

    filter_patterns = [
        r"(?i)^TEK DÜZEN.*",
        r"^\s*AKTİF\s*$",
        r"^\s*PASİF\s*$",
        r"^\s*Açıklama.*",
        r"^\s*\(?\d{4}\)?(?:\s*\(?\d{4}\)?)*\s*$",
        r"^\s*Cari Dönem\s*$",
        r"^\s*HESAP KODU.*",
        r"^\s*Enflasyon Düzeltmesi.*$",
    ]

    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if any(re.search(pat, line_stripped) for pat in filter_patterns):
            continue

        all_numeric_strings = re.findall(r"\d[\d\.\,]*", line_stripped)
        if not all_numeric_strings:
            continue

        numeric_values_float = [to_float_turkish(s) for s in all_numeric_strings]
        if not any(val is not None for val in numeric_values_float):
            continue             

        if len(numeric_values_float) >= 3:
            onceki_val, cari_val, inflation_val = numeric_values_float[-3:]
            has_inflation_column_from_header = True
        elif len(numeric_values_float) == 2:
            onceki_val, cari_val = numeric_values_float[-2:]
            inflation_val = None
        else:
            cari_val = numeric_values_float[-1] if numeric_values_float else None
            onceki_val = inflation_val = None             
        
        description, onceki_val, cari_val, inflation_val = parse_numeric_columns(line_stripped)        
        kod = find_account_code(block_name, description)
        
        data.append([
            kod,
            description,
            onceki_val,
            cari_val,
            inflation_val if has_inflation_column_from_header else None
        ])

    columns = ["Kod", "Açıklama", "Önceki Dönem", "Cari Dönem"]
    if has_inflation_column_from_header:
        columns.append("Cari Dönem (Enflasyonlu)")

    df = pd.DataFrame(data, columns=columns)
    return df, has_inflation_column_from_header

def get_bilanco_total_from_text(full_text, block_name="AKTİF"):
    total_line_pattern = (
        rf"(?i){block_name}\s*TOPLAMI\s*"
        rf"({num_val_pattern_str}(?:\s+{num_val_pattern_str})?(?:\s+{num_val_pattern_str})?)"
    )
    total_match = re.search(total_line_pattern, full_text, re.DOTALL | re.IGNORECASE)

    totals = {"onceki": 0, "cari": 0, "cari_enflasyon": 0}
    if total_match:
        numeric_strings = find_all_nums_in_line.findall(total_match.group(1))
        numeric_values = [
            to_float_turkish(s) for s in numeric_strings if to_float_turkish(s) is not None
        ]

        if len(numeric_values) >= 3:
            totals["onceki"], totals["cari"], totals["cari_enflasyon"] = numeric_values[:3]
        elif len(numeric_values) == 2:
            totals["onceki"], totals["cari"] = numeric_values
        elif len(numeric_values) == 1:
            totals["cari"] = numeric_values[0]

    return totals

def parse_bilanco_from_pdf(pdf_path: str, text_content=None) -> dict:
    if text_content:
        full_text = text_content
    else:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])

    if "PASİF" in full_text and "AKTİF" in full_text:
        aktif_text, rest_text = re.split(r"PASİF\s*(?:\n|$)", full_text, 1)
        pasif_text = re.split(r"(?i)(PASİF\s*TOPLAMI|GELİR\s*TABLOSU)", rest_text, 1)[0]
    else:
        split_match = re.split(r"AKTİF\s*TOPLAMI[^\n]*\n", full_text, 1)
        if len(split_match) > 1:
            aktif_text, pasif_text = split_match[0], split_match[1]
        else:
            aktif_text = full_text
            pasif_text = ""

    if "PASİF" not in pasif_text.upper() and "III." in pasif_text:
        pasif_text = "PASİF\n" + pasif_text

    muk = extract_mukellef_bilgileri(full_text)
    unvan = muk.get("unvan", "Bilinmiyor")
    donem = muk.get("donem", "Bilinmiyor")
    vkn = muk.get("vergi_kimlik_no", "Bilinmiyor")

    df_aktif, has_inflation_aktif = parse_table_block(aktif_text, "AKTİF")
    df_pasif, has_inflation_pasif = parse_table_block(pasif_text, "PASİF")

    if df_pasif is None or df_pasif.empty:
        df_pasif, has_inflation_pasif = parse_table_block(pasif_text, "III.")

    has_inflation = has_inflation_aktif or has_inflation_pasif
    aktif_toplamlar = get_bilanco_total_from_text(full_text, "AKTİF")
    pasif_toplamlar = get_bilanco_total_from_text(full_text, "PASİF")

    if aktif_toplamlar.get("cari_enflasyon", 0) or pasif_toplamlar.get("cari_enflasyon", 0):
        has_inflation = True

    aktif_list = df_aktif.to_dict(orient="records") if df_aktif is not None else []
    pasif_list = df_pasif.to_dict(orient="records") if df_pasif is not None else []

    return {
        "tur": "bilanco",
        "vergi_kimlik_no": vkn,
        "unvan": unvan,
        "donem": donem,
        "aktif": aktif_list,
        "pasif": pasif_list,
        "has_inflation": has_inflation,
        "toplamlar": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
        "direct_totals": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
        "veriler": {
            "aktif": aktif_list,
            "pasif": pasif_list,
            "toplamlar": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
            "has_inflation": has_inflation,
        },
    }

def find_gelir_kodu(aciklama_raw: str) -> str:
    original = aciklama_raw.strip()
    m = re.match(r"^\s*(\d{3})\s*[.\-]?\s*(.*)", original)
    if m:
        return m.group(1)

    if re.match(r"^\s*([A-ZÇĞİÖŞÜ]|[IVXLCDM]+)\.\s", original.upper()):
        return ""

    temiz = re.sub(r"[^\w\s]", "", original.lower())
    best_code, best_score = "", 0.0
    for grup, kod_tanim in GELIR_TABLOSU_HESAPLARI.items():
        for kod, tanim in kod_tanim.items():
            tanim_clean = re.sub(r"[^\w\s]", "", tanim.lower())
            if temiz == tanim_clean or temiz in tanim_clean:
                return kod
            if abs(len(temiz) - len(tanim_clean)) > 20:
                continue
            score = difflib.SequenceMatcher(None, temiz, tanim_clean).ratio()
            if score > best_score and score > 0.75:
                best_code, best_score = kod, score
    return best_code

def koddan_grup_bul(kod: str) -> str:
    for grup, alt in GELIR_TABLOSU_HESAPLARI.items():
        if kod in alt:
            return grup
    return "Diğer"

def parse_gelir_from_pdf(pdf_path: str, text_content=None) -> dict:
    if text_content:
        full_text = text_content
    else:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    muk   = extract_mukellef_bilgileri(full_text)
    unvan = muk.get("unvan", "Bilinmiyor")
    donem = muk.get("donem", "Bilinmiyor")
    vkn   = muk.get("vergi_kimlik_no", "Bilinmiyor")

    lines = full_text.splitlines()
    collecting = False
    tablo = []
    has_inflation = False

    # Ba\u015Fl\u0131ktan enflasyon kolonunu kontrol et
    # Baştan regex tanımları
    find_gelir_header = re.compile(r"GEL.R\s*TABLO", re.I)
    skip_header_terms = re.compile(r"BILAN.O|\bVE\b", re.I)
    
    header_idx = -1
    for i, line in enumerate(lines):
        # Regex ile ara
        if find_gelir_header.search(line):
            # Eğer satırda "Bilanço" veya "VE" varsa (örn: "Bilanço ve Gelir Tablosu"), bu başlık değildir
            if skip_header_terms.search(line):
                continue

            collecting = True
            header_idx = i
            # Gelecek 5 satırda 'enflasyon' geçiyor mu?
            hdr_context = " ".join(lines[i:i+6]).lower()
            if "enflasyon" in hdr_context:
                has_inflation = True
            continue

        if not collecting: continue

        # Header Filter: Skip lines that are just years or period headers
        line_clean = line.strip()
        # Matches (2023), 2023, (2022) (2023), etc.
        if re.match(r"^\s*\(?\d{4}\)?(?:\s*\(?\d{4}\)?)*\s*$", line_clean):
            continue
        # Matches "Cari Dönem", "Önceki Dönem"
        if re.search(r"(?:Cari|Önceki)\s*Dönem", line_clean, re.I):
            continue
        # Matches "Açıklama" header
        if re.search(r"^\s*Açıklama", line_clean, re.I):
            continue

        # Sayısal satır mı?
        nums = FIND_NUM.findall(line)
        if not nums and "D\u00F6nem Net Kar\u0131 veya Zarar\u0131" not in line:
            continue
            
        desc, onceki, cari, cari_enf = parse_numeric_columns(line)
        if onceki is None and cari is None and "D\u00F6nem Net Kar\u0131 veya Zarar\u0131" not in line:
            continue

        kod  = find_gelir_kodu(desc)
        grup = koddan_grup_bul(kod)

        if "(-)" in desc or kod in NEGATIVE_GELIR_CODES:
            if onceki is not None: onceki = -abs(onceki)
            if cari is not None: cari = -abs(cari)
            if cari_enf is not None: cari_enf = -abs(cari_enf)

        tablo.append({
            "kod": kod,
            "aciklama": desc,
            "grup": grup,
            "onceki_donem": onceki,
            "cari_donem": cari,
            "cari_donem_enflasyonlu": cari_enf if has_inflation else None
        })
        
        if "D\u00F6nem Net Kar\u0131 veya Zarar\u0131" in line:
            break

    return {
        "tur": "gelir",
        "vergi_kimlik_no": vkn,
        "unvan": unvan,
        "donem": donem,
        "tablo": tablo,
        "veriler": tablo,
        "has_inflation": has_inflation
    }

def _stripped_canon(s: str) -> str:
    import unicodedata
    if not s: return ""
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    s = s.replace("\ufffd", "?")
    s = re.sub(r"\s+", " ", s).strip().upper()
    s = s.replace("I", "I").replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
    return s

def parse_kdv_from_pdf(pdf_path, text_content=None):
    data, donem_adi, unvan, vkn = [], "Bilinmiyor", "Bilinmiyor", "Bilinmiyor"
    
    def add_header(title):
        data.append({"alan": f"§ {title}", "deger": "", "tip": "header"})
    def add_row(name, value="", kind="data"):
        data.append({"alan": name, "deger": value, "tip": kind})
        
    try:
        full_text = ""
        if text_content:
            full_text = text_content
        else:
            with pdfplumber.open(pdf_path) as pdf:            
                full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            
        muk = extract_mukellef_bilgileri(full_text)
        unvan = muk["unvan"]
        donem_adi = muk["donem"]
        vkn = muk["vergi_kimlik_no"]

        all_lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        
        # --- PHASE 1: SUMMARY FIELDS ---
        summaries = {
            "Toplam Matrah": [r"TOPLAM\s*MATRAH", r"MATRAH\s*TOPLAMI"],
            "Hesaplanan KDV": [r"HESAPLANAN\s*(?:KATMA|KDV)"],
            "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi": [r"DAHA\s*ONCE\s*INDIRIM\s*KONUSU", r"KDV.NIN\s*ILAVESI"],
            "Toplam KDV": [r"TOPLAM\s*(?:KATMA|KDV)"],
            "İndirimler Toplamı": [r"INDIRIMLER\s*TOPLAMI"],
            "İstisna Kapsamına Giren İşlemlere Ait Toplam Teslim ve Hizmet Tutarı": [r"ISTISNA\s*KAPSAMINA\s*GIREN", r"HIZMET\s*TUTARI"],
            "İade Edilebilir KDV": [r"IADE\s*EDILEBILIR\s*(?:KDV|KATMA)"],
            "Tecil Edilecek KDV": [r"TECIL\s*EDILECEK\s*(?:KDV|KATMA)"],
            "Ödenmesi Gereken KDV": [r"ODENMESI\s*GEREKEN\s*(?:KDV|KATMA|VERGI)"],
            "İade Edilmesi Gereken KDV": [r"IADE\s*EDILMESI\s*GEREKEN\s*(?:KDV|KATMA)"],
            "Sonraki Döneme Devreden KDV": [r"SONRAKI\s*DONEME\s*DEVREDEN"],
            "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Aylık)": [r"BEDEL\s*\(AYLIK\)"],
            "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)": [r"BEDEL\s*\(KUMULATIF\)"],
            "Kredi Kartı İle Tahsil Edilen Teslim ve Hizmetlerin KDV Dahil Karşılığını Teşkil Eden Bedel": [r"KREDI\s*KARTI\s*ILE\s*TAHSIL"]
        }

        found_summaries = {}
        for field_name, patterns in summaries.items():
            for i, line in enumerate(all_lines):
                u_line = _stripped_canon(line)
                if any(re.search(pat, u_line, re.I) for pat in patterns):
                    val = None
                    offsets = [0, -1, -2, -3, 1, 2] if "BEDEL" in u_line else [0, -1, 1, -2, 2]
                    for offset in offsets:
                        idx = i + offset
                        if 0 <= idx < len(all_lines):
                            nums = AMT_RE.findall(all_lines[idx])
                            if nums:
                                val = nums[-1]
                                break
                    if val:
                        found_summaries[field_name] = val
                        break

        # --- PHASE 2: DETAILED SECTIONS ---
        from collections import OrderedDict
        sections = OrderedDict([
            ("MATRAH DETAYI", []),
            ("İNDİRİMLER DETAYI", []),
            ("İSTİSNALAR VE İADE", [])
        ])
        
        cur_sec = None
        for i, line in enumerate(all_lines):
            u_line = _stripped_canon(line)
            
            # Robust Header detection (Supports both New and Old styles)
            if "MATRAH DETAYI" in u_line or "TEVKIFAT UYGULANMAYAN" in u_line or "KISMI TEVKIFAT UYGULANAN" in u_line: 
                cur_sec = "MATRAH DETAYI"
            elif any(x in u_line for x in ["INDIRIMLER DETAYI", "INDIRILECEK KDV", "ORANLARA GORE DAGILIMI", "INDIRIM TURU"]): 
                cur_sec = "İNDİRİMLER DETAYI"
            elif any(x in u_line for x in ["ISTISNALAR", "IADE HAKKI", "TAM ISTISNA"]):
                cur_sec = "İSTİSNALAR VE İADE"
            
            if not cur_sec: continue

            # Section Specific Parsing
            if cur_sec == "MATRAH DETAYI":
                # 1100, 616 etc.
                m1 = re.search(r"^(\d{4})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m1:
                    code, desc, mtr, oran, vrg = m1.groups()
                    desc = re.sub(r"\[.*?\]", "", desc).strip()
                    sections[cur_sec].append({"alan": f"{code} {desc} (%{oran}) - Matrah", "deger": mtr})
                    sections[cur_sec].append({"alan": f"{code} {desc} (%{oran}) - Vergi", "deger": vrg})
                    continue
                
                m2 = re.search(r"^(\d{3,4})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d+/\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m2:
                    code, desc, mtr, oran, tev, vrg = m2.groups()
                    desc = re.sub(r"\[.*?\]", "", desc).strip()
                    sections[cur_sec].append({"alan": f"{code} {desc} (%{oran}) - Matrah", "deger": mtr})
                    sections[cur_sec].append({"alan": f"{code} {desc} (%{oran}) - Vergi", "deger": vrg})
                    continue

                m3 = re.search(r"^(\d{3,4})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m3:
                    code, desc, mtr, vrg = m3.groups()
                    # Final check: is this actually an Istisna code? (300-499)
                    if 300 <= int(code) <= 499:
                        sections["İSTİSNALAR VE İADE"].append({"alan": f"{code} {desc} - Teslim Bedeli", "deger": mtr})
                        sections["İSTİSNALAR VE İADE"].append({"alan": f"{code} {desc} - İade Edilecek", "deger": vrg})
                    else:
                        sections[cur_sec].append({"alan": f"{code} {desc} - Matrah", "deger": mtr})
                        sections[cur_sec].append({"alan": f"{code} {desc} - Vergi", "deger": vrg})
                    continue
                    
                # OLD STYLE MATRAH DETAYI (No Codes!) e.g. "Yapım İşleri ile... 5.497.864,80 18 4/10 593.769,40"
                m_old_tev = re.search(r"^([A-Za-z].*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d+/\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", line)
                if m_old_tev:
                    desc, mtr, oran, tev, vrg = m_old_tev.groups()
                    desc = re.sub(r"\[.*?\]", "", desc).strip()
                    # Assign a pseudo code based on keyword for classification
                    pseudo_code = "616" if "YAPIM" in desc.upper() else "1100"
                    sections[cur_sec].append({"alan": f"{pseudo_code} {desc} (%{oran}) - Matrah", "deger": mtr})
                    sections[cur_sec].append({"alan": f"{pseudo_code} {desc} (%{oran}) - Vergi", "deger": vrg})
                    continue
                    
                m_old_norm = re.search(r"^([A-Za-z].*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", line)
                if m_old_norm and not "TOPLAM" in line.upper():
                    desc, mtr, oran, vrg = m_old_norm.groups()
                    desc = re.sub(r"\[.*?\]", "", desc).strip()
                    sections[cur_sec].append({"alan": f"1100 {desc} (%{oran}) - Matrah", "deger": mtr})
                    sections[cur_sec].append({"alan": f"1100 {desc} (%{oran}) - Vergi", "deger": vrg})
                    continue
                    
                # OLD STYLE TEXTLESS MATRAH e.g. "314.955,00 20 62.991,00"
                m_old_no_text = re.search(r"^\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$", line)
                if m_old_no_text:
                    mtr, oran, vrg = m_old_no_text.groups()
                    sections[cur_sec].append({"alan": f"1100 Tevkifat Uygulanmayan İşlem (%{oran}) - Matrah", "deger": mtr})
                    sections[cur_sec].append({"alan": f"1100 Tevkifat Uygulanmayan İşlem (%{oran}) - Vergi", "deger": vrg})
                    continue

            elif cur_sec == "İNDİRİMLER DETAYI":
                # Oran Dağılımı: 20 10.828.454,75 2.165.690,95
                m_dist = re.search(r"^\s*(\d{1,2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$", line)
                if m_dist:
                    oran, bedel, vergi = m_dist.groups()
                    sections[cur_sec].append({"alan": f"İndirim (%{oran}) - Matrah", "deger": bedel})
                    sections[cur_sec].append({"alan": f"İndirim (%{oran}) - Vergi", "deger": vergi})
                    continue

                m_code = re.search(r"^(\d{3})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m_code:
                    code, desc, val = m_code.groups()
                    sections[cur_sec].append({"alan": f"{code} {desc}", "deger": val})
                    continue
                    
                # OLD STYLE İNDİRİM (No Codes!) e.g. "Yurtiçi Alımlara İlişkin KDV 803.718,72"
                m_old_ind = re.search(r"(Yurtiçi Alımlara İlişkin KDV|Sorumlu Sıfatıyla|İthalde Ödenen KDV|Satıştan İade Edilen).*?(\d{1,3}(?:\.\d{3})*,\d{2})", line, re.I)
                if m_old_ind:
                    desc, val = m_old_ind.groups()
                    pseudo_code = "108" if "Yurtiçi" in desc else ("109" if "Sorumlu" in desc else ("103" if "Satıştan" in desc else "110"))
                    # If only matched prefix, expand it for better display
                    if "Sorumlu" in desc: desc = "Sorumlu Sıfatıyla Beyan Edilerek Ödenen KDV"
                    sections[cur_sec].append({"alan": f"{pseudo_code} {desc}", "deger": val})
                    continue

                if "ONCEKI DONEMDEN DEVREDEN" in u_line and "KDV" in u_line:
                    val = None
                    if AMT_RE.search(line): val = AMT_RE.search(line).group(1)
                    elif i+1 < len(all_lines) and AMT_RE.search(all_lines[i+1]): val = AMT_RE.search(all_lines[i+1]).group(1)
                    if val: sections[cur_sec].append({"alan": "Önceki Dönemden Devreden KDV", "deger": val})
                    continue

            elif cur_sec == "İSTİSNALAR VE İADE":
                # 3-column Istisna: 325 - Yem Teslimleri 40.303.351,55 0,00 2.154.899,31
                m_ist3 = re.search(r"^(\d{3,4})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m_ist3:
                    code, desc, mtr, temin, vrg = m_ist3.groups()
                    sections[cur_sec].append({"alan": f"{code} {desc} - Teslim Bedeli", "deger": mtr})
                    sections[cur_sec].append({"alan": f"{code} {desc} - İade Edilecek", "deger": vrg})
                    continue

                m_ist = re.search(r"^(\d{3,4})\s*[-–]\s*(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                if m_ist:
                    code, desc, val = m_ist.groups()
                    y_kdv = "0,00"
                    all_nums = AMT_RE.findall(line)
                    if len(all_nums) >= 2: y_kdv = all_nums[-1]
                    sections[cur_sec].append({"alan": f"{code} {desc} - Teslim Bedeli", "deger": val})
                    sections[cur_sec].append({"alan": f"{code} {desc} - İade Edilecek", "deger": y_kdv})
                    continue

        # --- PHASE 3: ORGANIZE FINAL DATA ---
        add_header("MATRAH")
        for f in ["Toplam Matrah", "Hesaplanan KDV", "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi", "Toplam KDV"]:
            add_row(f, found_summaries.get(f, "0,00"))

        add_header("İNDİRİMLER")
        add_row("İndirimler Toplamı", found_summaries.get("İndirimler Toplamı", "0,00"))

        for sec_name, rows in sections.items():
            if rows:
                add_header(sec_name)
                for r in rows: add_row(r["alan"], r["deger"])

        add_header("İSTİSNALAR VE İADE ÖZET")
        for f in ["İstisna Kapsamına Giren İşlemlere Ait Toplam Teslim ve Hizmet Tutarı", "İade Edilebilir KDV"]:
            add_row(f, found_summaries.get(f, "0,00"))

        add_header("SONUÇ HESAPLARI")
        for f in ["Tecil Edilecek KDV", "Ödenmesi Gereken KDV", "İade Edilmesi Gereken KDV", "Sonraki Döneme Devreden KDV"]:
            add_row(f, found_summaries.get(f, "0,00"))

        add_header("DİĞER BİLGİLER")
        for f in ["Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Aylık)", 
                  "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)", 
                  "Kredi Kartı İle Tahsil Edilen Teslim ve Hizmetlerin KDV Dahil Karşılığını Teşkil Eden Bedel"]:
            add_row(f, found_summaries.get(f, "0,00"))

        return {
            "tur": "kdv",
            "donem": donem_adi,
            "unvan": unvan,
            "vergi_kimlik_no": vkn,
            "veriler": data
        }
    except Exception as e:
        import traceback
        return {"hata": f"PDF Ayrıştırma Hatası: {str(e)}\n{traceback.format_exc()}"}
