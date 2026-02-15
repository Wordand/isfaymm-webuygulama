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
    Türkçe sayı formatını float'a çevirir. 
    Örn: '1.250,50' -> 1250.5, '(1.250,50)' -> -1250.5
    """
    if isinstance(s, (int, float)):
        return float(s)
    if s is None or pd.isna(s) or str(s).strip() in ['', '-', '.', ',']:
        return 0.0
    
    s = str(s).strip()
    
    # Negatif kontrolleri
    is_neg = False
    if (s.startswith('(') and s.endswith(')')) or s.endswith('-') or s.startswith('-'):
        is_neg = True
        s = s.replace('(', '').replace(')', '').replace('-', '').strip()

    if ',' in s:
        # TR Formatı: 1.234,56 -> 1234.56
        s = s.replace('.', '').replace(',', '.')
    else:
        # Virgül yoksa. Nokta binlik mi yoksa ondalık mı?
        # Örn: "1.250" (TR binlik) veya "1.25" (Ondalık)
        dot_count = s.count('.')
        if dot_count > 1:
            # Birden fazla nokta varsa kesin binlik ayracıdır. "1.000.000"
            s = s.replace('.', '')
        elif dot_count == 1:
            parts = s.split('.')
            if len(parts[1]) == 3:
                # Noktadan sonra tam 3 hane varsa binlik ayracı olma ihtimali %99.
                # İstisna: 1.001 gibi çok küçük sayılar. Ama mizanlarda genelde binliktir.
                s = s.replace('.', '')
            else:
                # 1.2 veya 1.25 gibi bir şeyse ondalık kalsın.
                pass
    
    try:
        val = float(s)
        return -val if is_neg else val
    except:
        return 0.0

def prepare_df(df_raw, column_name):
    if df_raw is None or df_raw.empty:
        raise ValueError('Boş tablo alındı')

    df_raw = df_raw.copy() # df_raw'ı kopyala
    col_map = {str(col).strip().lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'): col for col in df_raw.columns}

    kod_kolon = col_map.get('kod')
    aciklama_kolon = col_map.get('aciklama') or col_map.get('aciklama adi') or col_map.get('hesap adi') or col_map.get('aciklama')
    
    alternatifler = {
        'cari donem': ['tutar', 'bakiye', 'cari donem (enflasyonlu)', 'cari_donem_enflasyonlu', 'cari_donem', 'cari donem', 'donem', 'cari'],
        'onceki donem': ['onceki_donem', 'onceki donem', 'gecen donem', 'onceki'],
    }

    # Aranan kolonun normalize hali
    anahtar = str(column_name).lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c')
    
    # 1. Tam eşleşme ara
    ana_kolon = col_map.get(anahtar)
    
    # 2. Alternatifler içinde ara
    if not ana_kolon:
        search_keys = []
        if 'enflasyon' in anahtar:
            # Eğer anahtar enflasyon içeriyorsa, önce enflasyonlu alternatifleri dene
            search_keys = [alt for alt in alternatifler['cari donem'] if 'enflasyon' in alt] + [alt for alt in alternatifler['cari donem'] if 'enflasyon' not in alt]
        else: # 'cari' veya genel arama
            search_keys = alternatifler['cari donem']
            
        for alt in search_keys:
            if alt in col_map:
                ana_kolon = col_map[alt]
                break

    # 3. Yıl tespiti (Örn: "2022" veya "Önceki Dönem (2022)")
    if not ana_kolon:
        import re
        # Önce tam eşleşen yıl ara
        for col in df_raw.columns:
            if re.match(r'^\d{4}$', str(col).strip()):
                if str(col).strip() in anahtar: # Eğer anahtar yıl içeriyorsa (2022 gibi)
                    ana_kolon = col
                    break
        
        # Bulamadıysa, kolon isminin içinde yılı ara
        if not ana_kolon and re.search(r'\d{4}', anahtar):
            target_year = re.search(r'\d{4}', anahtar).group()
            for col in df_raw.columns:
                if target_year in str(col):
                    ana_kolon = col
                    break

    # 4. Final Fallback: En sağdaki mantıklı kolon
    if not ana_kolon:
        # Kod ve Açıklama kolonları hariç potansiyel kolonlar
        potential_cols = [c for c in df_raw.columns if c not in [kod_kolon, aciklama_kolon, 'grup', 'Grup']]
        if potential_cols:
            # Eğer 'cari', 'donem' veya 'tutar' içeren bir aday varsa onu tercih et
            candidates = [c for c in potential_cols if any(x in str(c).lower() for x in ['cari', 'donem', 'tutar'])]
            if candidates:
                # En sağdaki cari/dönem/tutar adayını seç
                ana_kolon = candidates[-1]
            else:
                # Hiç cari/dönem/tutar adayı yoksa, en sağdaki kolonu al
                ana_kolon = potential_cols[-1]

    # Önceki Dönem tespiti
    onceki_kolon = None
    for alt in alternatifler['onceki donem']:
        if alt in col_map and col_map[alt] != ana_kolon: # ana_kolon ile çakışma kontrolü
            onceki_kolon = col_map[alt]
            break

    # Güvenli kolon listesi
    kolonlar = []
    if kod_kolon: kolonlar.append(kod_kolon)
    if aciklama_kolon: kolonlar.append(aciklama_kolon)
    if ana_kolon: kolonlar.append(ana_kolon)
    if onceki_kolon and onceki_kolon != ana_kolon: kolonlar.append(onceki_kolon)

    if not ana_kolon and not kod_kolon:
        raise ValueError('Kritik kolonlar (Kod/Dönem) bulunamadı.')

    df = df_raw[kolonlar].copy()
    
    # Standartlaştırma
    rename_map = {}
    if ana_kolon: rename_map[ana_kolon] = 'Cari Dönem'
    if onceki_kolon: rename_map[onceki_kolon] = 'Önceki Dönem'
    if kod_kolon: rename_map[kod_kolon] = 'Kod'
    if aciklama_kolon: rename_map[aciklama_kolon] = 'Açıklama'
    df.rename(columns=rename_map, inplace=True)
    
    # Sayısal dönüşüm
    def safe_conv(val):
        if isinstance(val, str):
            val = to_float_turkish(val)
        try:
            return float(val) if val is not None else 0.0
        except:
            return 0.0

    for col in ['Cari Dönem', 'Önceki Dönem']:
        if col in df.columns:
            df[col] = df[col].apply(safe_conv)
    
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
