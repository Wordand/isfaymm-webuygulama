
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
import os
from cryptography.fernet import Fernet

def to_float_turkish(s):
    if isinstance(s, (int, float)):
        return float(s)
    if s is None or pd.isna(s) or str(s).strip() in ['', '-', '.', ',']:
        return 0.0
    s = str(s).strip()
    is_neg = False
    if (s.startswith('(') and s.endswith(')')) or s.endswith('-') or s.startswith('-'):
        is_neg = True
        s = s.replace('(', '').replace(')', '').replace('-', '').strip()
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        dot_count = s.count('.')
        if dot_count > 1:
            s = s.replace('.', '')
        elif dot_count == 1:
            parts = s.split('.')
            if len(parts[1]) == 3:
                s = s.replace('.', '')
    try:
        val = float(s)
        return -val if is_neg else val
    except:
        return 0.0

def kt(df, codes, target_col="Cari Dönem"):
    if df is None or df.empty: return 0.0
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    if "Kod" not in df.columns or target_col not in df.columns: return 0.0
    df["_kod_norm"] = df["Kod"].astype(str).str.strip().str.replace(r'\.0+$', '', regex=True)
    df["_desc_norm"] = df["Açıklama"].astype(str).str.upper().str.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
    search_list = [str(c).strip().replace(".0", "") for c in codes]
    search_set = set(search_list)
    KEYWORD_MAP = {
        "1": "DONEN VARLIK", "2": "DURAN VARLIK", "3": "KISA VADELI YABANCI", "4": "UZUN VADELI YABANCI", "5": "OZKAYNAK",
        "60": "BRUT SATIS", "61": "SATIS INDIRIM", "62": "SATISLARIN MALIYETI", "63": "FAALIYET GIDERI",
        "64": "OLAGAN GELIR", "65": "OLAGAN GIDER", "66": "FINANSMAN GIDERI",
        "690": "DONEM KARI", "692": "DONEM NET KARI"
    }
    final_values = []
    already_accounted_prefixes = []
    for idx, row in df.iterrows():
        code = row["_kod_norm"]
        desc = row["_desc_norm"]
        val = row[target_col]
        is_match = False
        if code in search_set: is_match = True
        else:
            for sc in search_list:
                if code.startswith(sc) and (len(code) == len(sc) or code[len(sc)] in ('.', ' ', '-', '_', '/') or code[len(sc)].isdigit()):
                    is_match = True
                    break
        if not is_match or (isinstance(val, (int, float)) and val < 100):
            for sc in search_list:
                if sc in KEYWORD_MAP and KEYWORD_MAP[sc] in desc:
                    is_match = True
                    break
        if is_match:
            is_child = False
            for p in already_accounted_prefixes:
                if code != "" and code.startswith(p) and code != p:
                    is_child = True
                    break
            if not is_child:
                num_val = to_float_turkish(val)
                final_values.append(num_val)
                if code != "": already_accounted_prefixes.append(code)
    return float(sum(final_values))

# DB details
DB_URL = "postgresql://postgres:lalelale@localhost:5432/tesvik_db"
FERNET_KEY = b'fS3_v0rM6j7D4-R_K_9R8-7H5-4G3-2F1-E0D9C8B7A6=' # Default or from app.py
fernet = Fernet(FERNET_KEY)

vkn = '0330382441'
yil = '2022'

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get Bilanco
cur.execute("SELECT b.veriler FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.vergi_kimlik_no=%s AND b.donem LIKE %s AND b.tur='bilanco' LIMIT 1", (vkn, f"{yil}%"))
rb = cur.fetchone()
# Get Gelir
cur.execute("SELECT b.veriler FROM beyanname b JOIN mukellef m ON b.mukellef_id=m.id WHERE m.vergi_kimlik_no=%s AND b.donem LIKE %s AND b.tur='gelir' LIMIT 1", (vkn, f"{yil}%"))
rg = cur.fetchone()

if rb and rg:
    pb = json.loads(fernet.decrypt(rb["veriler"].tobytes() if isinstance(rb["veriler"], memoryview) else rb["veriler"]).decode("utf-8"))
    pg = json.loads(fernet.decrypt(rg["veriler"].tobytes() if isinstance(rg["veriler"], memoryview) else rg["veriler"]).decode("utf-8"))
    
    # Simple rename logic for test
    from services.utils import prepare_df
    # Mocking prepare_df or just use the logic
    # Actually I need the real prepare_df behavior
    
    # For now, let's just see the raw data for Gelir
    gelir_tablo = pg.get("tablo", [])
    df_gelir_raw = pd.DataFrame(gelir_tablo)
    print("RAW GELIR COLS:", df_gelir_raw.columns.tolist())
    
    # Identify target column
    target_col = "Cari Dönem"
    # Rename for kt
    df_gelir = df_gelir_raw.copy()
    column_mapping = {
        'kod': 'Kod', 'aciklama': 'Açıklama', 'cari_donem': 'Cari Dönem', 'cari donem': 'Cari Dönem'
    }
    df_gelir.rename(columns=column_mapping, inplace=True)
    
    print("\nTESTING kt for 2022 Profitability:")
    brut_satislar = kt(df_gelir, ["60", "600", "601", "602"])
    satis_indirimleri = kt(df_gelir, ["61", "610", "611", "612"])
    faaliyet_giderleri = kt(df_gelir, ["63"])
    net_kar = kt(df_gelir, ["692"])
    
    print(f"Brut Satislar: {brut_satislar}")
    print(f"Satis Indirimleri: {satis_indirimleri}")
    print(f"Net Satislar: {brut_satislar - abs(satis_indirimleri)}")
    print(f"Net Kar: {net_kar}")
    
    # Detail search for 60
    print("\nROWS MATCHING 60:")
    for idx, row in df_gelir.iterrows():
        c = str(row.get("Kod", "")).strip()
        d = str(row.get("Açıklama", "")).strip()
        v = row.get("Cari Dönem")
        if c.startswith("60") or "BRUT SATIS" in d.upper():
            print(f"Kod: '{c}' | Desc: '{d}' | Val: {v}")

else:
    print("NO DATA FOUND IN DB")
