from datetime import datetime
import pandas as pd
import re
from jinja2 import Undefined
import config

ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def safe_date(value):
    """Hem datetime hem string değerler için güvenli tarih formatı döner."""
    if not value:
        return "-"
    try:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                try:
                    value = datetime.strptime(value, "%d.%m.%Y")
                except Exception:
                    return value  # Tanınmazsa orijinal haliyle bırak
        return value.strftime("%d.%m.%Y")
    except Exception:
        return str(value)

def tlformat(value):
    if value is None or isinstance(value, Undefined):
        return "-"
    try:
        return '{:,.2f}'.format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)

def currency_filter(amount):
    try:
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return amount or "-"

def to_float_turkish(s):
    """
    Türk Lirası formatındaki sayısal stringi (örneğin '1.234,56', '(1.234,56)', '1.234,56 -') float'a dönüştürür.
    """
    if isinstance(s, (int, float)):
        return s

    if s is None or pd.isna(s) or str(s).strip() == '':
        return None
    
    s = str(s).strip() 
    
    is_negative_parentheses = False
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1] 
        is_negative_parentheses = True
    
    is_negative_trailing_dash = False
    if s.endswith('-'):
        s = s[:-1].strip() 
        is_negative_trailing_dash = True
  
    s = s.replace('.', '').replace(',', '.')
    
    try:
        float_val = float(s)
        if is_negative_parentheses or is_negative_trailing_dash:
            float_val = -float_val
        return float_val
    except ValueError:
        return None

def prepare_df(df_raw, column_name):
    if df_raw is None or df_raw.empty:
        raise ValueError('Boş tablo alındı')

    # --- Kolon adlarını normalize et ---
    col_map = {col.strip().lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'): col for col in df_raw.columns}

    alternatifler = {
        'cari donem': ['cari_donem', 'cari donem', 'donem', 'cari'],
        'onceki donem': ['onceki_donem', 'onceki donem', 'gecen donem', 'onceki'],
    }

    anahtar = column_name.lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
    ana_kolon = col_map.get(anahtar)
    if not ana_kolon and anahtar in alternatifler:
        for alt in alternatifler[anahtar]:
            if alt in col_map:
                ana_kolon = col_map[alt]
                break

    onceki_kolon = None
    for alt in alternatifler['onceki donem']:
        if alt in col_map:
            onceki_kolon = col_map[alt]
            break

    kod_kolon = col_map.get('kod')
    aciklama_kolon = col_map.get('aciklama') or col_map.get('aciklama adi') or col_map.get('hesap adi')

    # --- Güvenli kolon kontrolü ---
    kolonlar = [k for k in [kod_kolon, aciklama_kolon, ana_kolon] if k]
    if not kolonlar:
        raise ValueError('Kolon eşleşmesi yapılamadı: Kod, Açıklama veya Dönem sütunu bulunamadı.')

    df = df_raw[kolonlar].copy()

    # --- Kolon adlarını standartlaştır ---
    rename_map = {}
    if kod_kolon: rename_map[kod_kolon] = 'Kod'
    if aciklama_kolon: rename_map[aciklama_kolon] = 'Açıklama'
    if ana_kolon: rename_map[ana_kolon] = 'Cari Dönem'
    df.rename(columns=rename_map, inplace=True)

    # --- Önceki dönem ekle ---
    if onceki_kolon:
        df.loc[:, 'Önceki Dönem'] = pd.to_numeric(df_raw[onceki_kolon], errors='coerce').fillna(0)
    else:
        df.loc[:, 'Önceki Dönem'] = 0

    # --- Sayısal dönüşüm ---
    if 'Cari Dönem' in df.columns:
        df.loc[:, 'Cari Dönem'] = pd.to_numeric(df['Cari Dönem'], errors='coerce').fillna(0)

    # --- Kolon sırasını düzenle ---
    hedef_sira = ['Kod', 'Açıklama', 'Önceki Dönem', 'Cari Dönem']
    df = df[[c for c in hedef_sira if c in df.columns] + [c for c in df.columns if c not in hedef_sira]]

    return df

def mon2num(mon: str) -> int:
    m = mon.upper().strip()
    m = (m
         .replace('Ş','S').replace('Ğ','G').replace('İ','I').replace('Ü','U').replace('Ö','O').replace('Ç','C'))
    MAP = {
        'OCAK':1, 'SUBAT':2, 'MART':3, 'NISAN':4, 'MAYIS':5, 'HAZIRAN':6,
        'TEMMUZ':7, 'AGUSTOS':8, 'EYLUL':9, 'EKIM':10, 'KASIM':11, 'ARALIK':12
    }
    return MAP.get(m, 99)

def month_key(col: str):
    try:
        if '/' in col:
            yil_str, ay_str = col.split('/', 1)
            return (int(yil_str), mon2num(ay_str))
        return (9999, 99)
    except Exception:
        return (9999, 99)
