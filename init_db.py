import os
import sqlite3
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()

if not DATABASE_URL:
    raise ValueError("DATABASE_URL bulunamadı. Lütfen .env veya Render environment değişkenlerini kontrol et.")

# ======================================================
# 1️⃣ Yerel (SQLite) Ortam
# ======================================================
if DATABASE_URL.startswith("sqlite:///"):
    print("🧩 Yerel geliştirme ortamı algılandı — SQLite kullanılacak.")
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # --- USERS TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_approved INTEGER DEFAULT 0
    );
    """)

    # --- MÜKELLEF TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS mukellef (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        vergi_kimlik_no TEXT NOT NULL,
        unvan TEXT NOT NULL,
        UNIQUE(user_id, vergi_kimlik_no)
    );
    """)
    
    

    # --- BEYANNAME TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS beyanname (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mukellef_id INTEGER NOT NULL,
        donem TEXT NOT NULL,
        tur TEXT NOT NULL,
        veriler BLOB,
        yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, mukellef_id, donem, tur)
    );
    """)

    # --- TEŞVİK BELGELERİ TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mukellef_id INTEGER,
        yukleme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
        belge_no TEXT,
        belge_tarihi TEXT,
        karar TEXT,
        program_turu TEXT,
        yatirim_turu1 TEXT,
        yatirim_turu2 TEXT,
        vize_durumu TEXT,
        donem TEXT,
        il TEXT,
        osb TEXT,
        bolge TEXT,
        katki_orani REAL,
        vergi_orani REAL,
        diger_oran REAL,
        toplam_tutar REAL,
        katki_tutari REAL,
        diger_katki_tutari REAL,
        cari_harcama_tutari REAL,
        toplam_harcama_tutari REAL,
        fiili_katki_tutari REAL,
        endeks_katki_tutari REAL,
        onceki_yatirim_katki_tutari REAL,
        onceki_diger_katki_tutari REAL,
        onceki_katki_tutari REAL,
        cari_yatirim_katki REAL DEFAULT 0.0,
        cari_diger_katki REAL DEFAULT 0.0,
        cari_toplam_katki REAL DEFAULT 0.0,
        genel_toplam_katki REAL DEFAULT 0.0,
        brut_satis REAL,
        ihracat REAL,
        imalat REAL,
        diger_faaliyet REAL,
        use_detailed_profit_ratios INTEGER DEFAULT 0
    );
    """)



    # --- PROFIT DATA TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS profit_data (
        user_id INTEGER NOT NULL,
        aciklama_index INTEGER NOT NULL,
        column_b REAL DEFAULT 0.0,
        column_c REAL DEFAULT 0.0,
        column_d REAL DEFAULT 0.0,
        column_e REAL DEFAULT 0.0,
        PRIMARY KEY (user_id, aciklama_index)
    );
    """)




    # --- TEŞVİK KULLANIM TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS tesvik_kullanim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        belge_no TEXT NOT NULL,
        hesap_donemi INTEGER NOT NULL,
        yatirim_kazanci REAL DEFAULT 0.0,
        diger_kazanc REAL DEFAULT 0.0,
        cari_yatirim_katkisi REAL DEFAULT 0.0,
        cari_diger_katkisi REAL DEFAULT 0.0,
        genel_toplam_katki REAL DEFAULT 0.0,
        kalan_katki REAL DEFAULT 0.0,
        kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, belge_no, hesap_donemi)
    );
    """)

    conn.commit()
    conn.close()
    print("✅ SQLite veritabanı başarıyla oluşturuldu.")
    exit()


# ======================================================
# 2️⃣ Production (PostgreSQL / Supabase)
# ======================================================
print("☁️ Production ortam algılandı — PostgreSQL (Supabase) kullanılacak.")
conn = psycopg.connect(DATABASE_URL)
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
    yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, mukellef_id, donem, tur)
);
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS profit_data (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    aciklama_index INTEGER NOT NULL,
    column_b DOUBLE PRECISION DEFAULT 0.0,
    column_c DOUBLE PRECISION DEFAULT 0.0,
    column_d DOUBLE PRECISION DEFAULT 0.0,
    column_e DOUBLE PRECISION DEFAULT 0.0,
    PRIMARY KEY (user_id, aciklama_index)
);
""")


# --- TEŞVİK BELGELERİ TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mukellef_id INTEGER REFERENCES mukellef(id) ON DELETE CASCADE,
    yukleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    belge_no TEXT,
    belge_tarihi TEXT,
    karar TEXT,
    program_turu TEXT,   -- ✅ EKLENDİ
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

# --- TEŞVİK KULLANIM TABLOSU ---
cur.execute("""
CREATE TABLE IF NOT EXISTS tesvik_kullanim (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    belge_no TEXT NOT NULL,
    hesap_donemi INT NOT NULL,
    yatirim_kazanci DOUBLE PRECISION DEFAULT 0.0,
    diger_kazanc DOUBLE PRECISION DEFAULT 0.0,
    cari_yatirim_katkisi DOUBLE PRECISION DEFAULT 0.0,
    cari_diger_katkisi DOUBLE PRECISION DEFAULT 0.0,
    genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
    kalan_katki DOUBLE PRECISION DEFAULT 0.0,
    kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, belge_no, hesap_donemi)
);
""")

# --- İNDEKSLER ---
cur.execute("CREATE INDEX IF NOT EXISTS idx_mukellef_user ON mukellef(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_tesvik_user ON tesvik_belgeleri(user_id);")

conn.commit()
cur.close()
conn.close()

print("✅ PostgreSQL veritabanı başarıyla oluşturuldu (Supabase bağlantısı ile).")
