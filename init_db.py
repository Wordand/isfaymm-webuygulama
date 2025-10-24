import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

# Ortam değişkeninden DATABASE_URL al
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL bulunamadı. Lütfen .env veya Render environment değişkenlerini kontrol et.")

# PostgreSQL bağlantısı
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# --- USERS TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_approved INTEGER DEFAULT 0
);
""")

# --- MATRAHLAR TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS matrahlar (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gelir DOUBLE PRECISION,
    gider DOUBLE PRECISION,
    matrah DOUBLE PRECISION,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# --- MÜKELLEF TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS mukellef (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vergi_kimlik_no TEXT NOT NULL,
    unvan TEXT NOT NULL,
    UNIQUE(user_id, vergi_kimlik_no)
);
""")

# --- BEYANNAME TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS beyanname (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mukellef_id INTEGER NOT NULL REFERENCES mukellef(id) ON DELETE CASCADE,
    donem TEXT NOT NULL,
    tur TEXT NOT NULL,
    veriler BYTEA,
    dosya_adi TEXT,
    yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, mukellef_id, donem, tur)
);
""")

# --- TEŞVİK BELGELERİ TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dosya_adi TEXT NOT NULL,
    yukleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    belge_no TEXT,
    belge_tarihi TEXT,
    karar TEXT,
    yatirim_turu1 TEXT,
    yatirim_turu2 TEXT,
    vize_durumu TEXT,
    donem TEXT,
    il TEXT,
    osb TEXT,
    bolge TEXT,

    katki_orani DOUBLE PRECISION,
    vergi_orani DOUBLE PRECISION,
    diger_oran DOUBLE PRECISION,

    toplam_tutar DOUBLE PRECISION,
    katki_tutari DOUBLE PRECISION,
    diger_katki_tutari DOUBLE PRECISION,
    cari_harcama_tutari DOUBLE PRECISION,
    toplam_harcama_tutari DOUBLE PRECISION,
    fiili_katki_tutari DOUBLE PRECISION,
    endeks_katki_tutari DOUBLE PRECISION,

    onceki_yatirim_katki_tutari DOUBLE PRECISION,
    onceki_diger_katki_tutari DOUBLE PRECISION,
    onceki_katki_tutari DOUBLE PRECISION,

    cari_yatirim_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_diger_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
    genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,

    brut_satis DOUBLE PRECISION,
    ihracat DOUBLE PRECISION,
    imalat DOUBLE PRECISION,
    diger_faaliyet DOUBLE PRECISION,
    use_detailed_profit_ratios BOOLEAN DEFAULT FALSE
);
""")

# --- PROFIT_DATA TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS profit_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    aciklama_index INTEGER NOT NULL,
    column_b DOUBLE PRECISION DEFAULT 0.0,
    column_c DOUBLE PRECISION DEFAULT 0.0,
    column_d DOUBLE PRECISION DEFAULT 0.0,
    column_e DOUBLE PRECISION DEFAULT 0.0,
    UNIQUE(user_id, aciklama_index)
);
""")

# --- İNDEKSLER ---
cur.execute("CREATE INDEX IF NOT EXISTS idx_mukellef_user ON mukellef(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_beyanname_user ON beyanname(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_tesvik_user ON tesvik_belgeleri(user_id);")

# Kaydet ve kapat
conn.commit()
cur.close()
conn.close()

print("✅ PostgreSQL veritabanı başarıyla oluşturuldu (Supabase bağlantısı ile).")
