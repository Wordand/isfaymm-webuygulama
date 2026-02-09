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

    # --- Tür ---
    text_upper = text.upper()
    if "KURUMLAR VERGİSİ BEYANNAMESİ" in text_upper:
        tur = "Kurumlar"
        if "Bilanço" in text or "Kazancın Tespit Yöntemi Bilanço" in text:
            tur = "Bilanço"
        elif "GELİR TABLOSU" in text:
            tur = "Gelir Tablosu"
    elif "KATMA DEĞER VERGİSİ BEYANNAMESİ" in text_upper:
        tur = "KDV"

    # --- VKN ---
    m_vkn = re.search(r"Vergi Kimlik (?:No|Numaras\u0131)(?:\s*\(TC Kimlik No\))?\s+(\d{10,11})", text, re.I)
    if m_vkn:
        vkn = m_vkn.group(1).strip()
    else:
        # Alternatif VKN arama
        m_vkn2 = re.search(r"Kimlik\s+Numaras\u0131\s+(\d{10,11})", text, re.I)
        if m_vkn2: vkn = m_vkn2.group(1).strip()

    # --- Unvan ---
    # Kurumlar beyannamesinde unvan genelde "Soyad\u0131, Ad\u0131 (Unvan\u0131)" veya "Soyad\u0131 (Unvan\u0131)" alt\u0131nda olur
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"Soyad\u0131,? Ad\u0131 \(Unvan\u0131\)|Soyad\u0131 \(Unvan\u0131\)", line, re.I):
            # Hemen yan\u0131ndaysa
            match = re.search(r"(?:Unvan\u0131\))\s+([^\n]+)", line, re.I)
            if match and len(match.group(1).strip()) > 3:
                unvan = match.group(1).strip().upper()
                break
            # Bir sonraki sat\u0131rdaysa
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if len(next_line) > 3:
                    unvan = next_line.upper()
                    # E\u011fer devam\u0131 da varsa (Ad\u0131 (Unvan\u0131n Devam\u0131))
                    if i + 2 < len(lines) and "ADININ DEVAMI" not in lines[i+2].upper():
                         unvan += " " + lines[i+2].strip().upper()
                    break

    # --- Dönem ---
    if tur == "KDV":
        m1 = re.search(r"Y\u0131l\s+(\d{4}).*?Ay\s+([A-Za-z\u00C7\u00D6\u015E\u0130\u00DC\u011E\u00E7\u00F6\u015F\u0131\u00FC\u011F]+)", text, re.IGNORECASE | re.DOTALL)
        m2 = re.search(r"Ay\s+([A-Za-z\u00C7\u00D6\u015E\u0130\u00DC\u011E\u00E7\u00F6\u015F\u0131\u00FC\u011F]+).*?Y\u0131l\s+(\d{4})", text, re.IGNORECASE | re.DOTALL)
        if m1:
            donem = f"{m1.group(2).capitalize()} / {m1.group(1)}"
        elif m2:
            donem = f"{m2.group(1).capitalize()} / {m2.group(2)}"
    else:
        # Kurumlar i\u00E7in tablo ba\u015Fl\u0131klar\u0131ndaki y\u0131llar\u0131 yakala: (2024)
        m_yil = re.search(r"Cari D\u00F6nem\s*\n\s*\((\d{4})\)", text, re.I)
        if m_yil:
            donem = m_yil.group(1)
        else:
            m3 = re.search(r"D\u00D6NEM T\u0130P\u0130.*?Y\u0131l\s+(\d{4})", text, re.IGNORECASE | re.DOTALL)
            if m3:
                donem = m3.group(1)
            else:
                m4 = re.search(r"D\u00D6NEM[:\s]+(\d{4})", text)
                if m4:
                    donem = m4.group(1)

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

def parse_bilanco_from_pdf(pdf_path: str) -> dict:
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

def parse_gelir_from_pdf(pdf_path: str) -> dict:
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
    header_idx = -1
    for i, line in enumerate(lines):
        if "GEL\u0130R TABLOSU" in line.upper():
            collecting = True
            header_idx = i
            # Gelecek 5 sat\u0131rda 'enflasyon' ge\u00E7iyor mu?
            hdr_context = " ".join(lines[i:i+6]).lower()
            if "enflasyon" in hdr_context:
                has_inflation = True
            continue

        if not collecting: continue

        # Say\u0131sal sat\u0131r m\u0131?
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
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def parse_kdv_from_pdf(pdf_path):
    data, donem_adi, unvan, vkn = [], "Bilinmiyor", "Bilinmiyor", "Bilinmiyor"
    
    def norm(s): return re.sub(r"\s+", " ", s).strip()
    def amt(s):
        m = AMT_RE.search(s)
        return m.group(1) if m else "0,00"
    def add_header(title):
        data.append({"alan": f"§ {title}", "deger": "", "tip": "header"})
    def add_row(name, value="", kind="data"):
        data.append({"alan": name, "deger": value, "tip": kind})
    def ensure_header(title):
        for i in range(len(data) - 1, -1, -1):
            if data[i].get("tip") == "header":
                if data[i]["alan"] == f"§ {title}":
                    return
                break
        add_header(title)
        
    try:
        with pdfplumber.open(pdf_path) as pdf:            
            full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            if "KURUMLAR VERGİSİ BEYANNAMESİ" in full_text.upper():
                return {
                    "tur": "kurumlar",
                    "donem": "Bilinmiyor",
                    "unvan": "Bilinmiyor",
                    "vergi_kimlik_no": "Bilinmiyor",
                    "veriler": [],
                    "hata": "Bu dosya Kurumlar Vergisi beyannamesi, KDV değil."
                }
            
            muk = extract_mukellef_bilgileri(full_text)
            unvan = muk["unvan"]
            donem_adi = muk["donem"]
            vkn = muk["vergi_kimlik_no"]

            cur_sec = None
            other_hdr_added = False
            in_matrah_block = False 
            SUM_CANON = { _stripped_canon(k): v for k, v in SUMMARY_REDIRECT.items() }            

            for page in pdf.pages:
                lines = (page.extract_text() or "").split("\n")
                consumed = set()         
                
                for i, line in enumerate(lines):
                    if i in consumed:
                        continue
                    
                    U = _stripped_canon(line)

                    if _stripped_canon("Matrah Toplamı") in U:
                        ensure_header("MATRAH TOPLAMI")
                        add_row("Matrah Toplamı", amt(line))
                        in_matrah_block = True
                        continue

                    if in_matrah_block:
                        matched_summary = False
                        for k_can, shown_name in SUM_CANON.items():
                            if k_can in U:
                                ensure_header("MATRAH TOPLAMI")
                                add_row(shown_name, amt(line))
                                matched_summary = True
                                break
                        if matched_summary:
                            continue

                    if "MATRAH TOPLAMI" in U:
                        ensure_header("MATRAH TOPLAMI")
                        add_row("Matrah Toplamı", amt(line))
                        in_matrah_block = True
                        continue

                    if "TECIL EDILECEK KATMA DEGER VERGISI" in U:
                        ensure_header("SONUÇ")
                        add_row("Tecil Edilecek Katma Değer Vergisi", amt(line))
                    if "BU DONEMDE ODENMESI GEREKEN KATMA DEGER VERGISI" in U:
                        ensure_header("SONUÇ")
                        add_row("Bu Dönemde Ödenmesi Gereken Katma Değer Vergisi", amt(line))
                        continue

                    if all(x in U for x in ["ISLEM", "TURU", "MATRAH", "VERG"]):
                        ctx = " ".join(_stripped_canon(l) for l in lines[max(0, i-2): i+3])
                        if _stripped_canon("DİĞER İŞLEMLER") in ctx:
                            if not other_hdr_added:
                                add_header("DİĞER İŞLEMLER")
                                other_hdr_added = True
                            cur_sec = "DİĞER İŞLEMLER"
                            in_matrah_block = False
                            continue

                    sec = None
                    for k in SECTION_KEYS:
                        if U == _stripped_canon(k):
                            sec = k
                            break
                    if not sec:
                        for wrong, right in SECTION_ALIASES.items():
                            if U == _stripped_canon(wrong):
                                sec = right
                                break
                    
                    if sec:
                        in_matrah_block = False
                        cur_sec = sec
                        add_header(sec)
                        if sec == "DİĞER İŞLEMLER": other_hdr_added = True
                        continue

                    if cur_sec == "TEVKİFAT UYGULANMAYAN İŞLEMLER":
                        m = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                        for matrah, oran, vergi in m:
                            add_row(f"Tevkifatsız İşlem (%{oran}) - Matrah", matrah)
                            add_row(f"Tevkifatsız İşlem (%{oran}) - Vergi", vergi)
                        continue

                    if cur_sec == "KISMİ TEVKİFAT UYGULANAN İŞLEMLER":
                        mk = re.search(r"^(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d+/\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", line)
                        if mk:
                            desc = norm(mk.group(1))
                            add_row(f"{desc} - Matrah", mk.group(2))
                            add_row(f"{desc} - KDV Oranı", f"{mk.group(3)}%")
                            add_row(f"{desc} - Tevkifat Oranı", mk.group(4))
                            add_row(f"{desc} - Vergi", mk.group(5))
                            continue
                        
                        window_lines = lines[i:i+5]
                        window = " ".join(window_lines)
                        mk2 = re.search(r"(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d+/\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", window)
                        if mk2:
                            desc = norm(mk2.group(1))
                            vergi_str  = mk2.group(5)
                            add_row(f"{desc} - Matrah", mk2.group(2))
                            add_row(f"{desc} - KDV Oranı", f"{mk2.group(3)}%")
                            add_row(f"{desc} - Tevkifat Oranı", mk2.group(4))
                            add_row(f"{desc} - Vergi", vergi_str)
                            
                            end_offset = 0
                            for j, wl in enumerate(window_lines):
                                if vergi_str in wl:
                                    end_offset = j
                                    break
                            for k in range(1, end_offset+1):
                                consumed.add(i+k)
                            continue

                    if cur_sec != "DİĞER İŞLEMLER" and re.search(r"(ALINAN MALLARIN İADESI|AMORT[Iİ]S?MAN)", _stripped_canon(line), re.I):
                        nums_tmp = AMT_RE.findall(line)
                        if len(nums_tmp) >= 2:
                            if not other_hdr_added:
                                add_header("DİĞER İŞLEMLER")
                                other_hdr_added = True
                            cur_sec = "DİĞER İŞLEMLER"

                    if cur_sec == "DİĞER İŞLEMLER":
                        mk = re.search(r"^(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", line)
                        if mk:
                            add_row(f"{norm(mk.group(1))} - Matrah", mk.group(2))
                            add_row(f"{norm(mk.group(1))} - Vergi", mk.group(3))
                            continue
                        
                        window = " ".join(lines[i:i+4])
                        mk2 = re.search(r"(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})", window)
                        if mk2:
                            add_row(f"{norm(mk2.group(1))} - Matrah", mk2.group(2))
                            add_row(f"{norm(mk2.group(1))} - Vergi", mk2.group(3))
                             # Note: skipping accurate consumption logic for simplicity in this port, assuming 1 line mostly
                            continue

    except Exception as e:
        print(f"PDF Parsing Error: {e}")
        return {"hata": str(e)}

    return {
        "tur": "kdv",
        "donem": donem_adi,
        "unvan": unvan,
        "vergi_kimlik_no": vkn,
        "veriler": data
    }
