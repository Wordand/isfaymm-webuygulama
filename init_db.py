import os
import sqlite3
import psycopg2 # Use psycopg2 to match requirements.txt
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


    # --- USERS TABLOSU (SQLite) ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_approved INTEGER DEFAULT 0,
        is_suspended INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login TEXT,
        admin_notes TEXT
    );
    """)


    # --- MÜKELLEF TABLOSU ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS mukellef (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        vergi_kimlik_no TEXT NOT NULL,
        unvan TEXT NOT NULL,
        vergi_dairesi TEXT,
        ilgili_memur TEXT,
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


    c.execute("""
    CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Zorunlu İlişkiler ve Kimlikler
        user_id INTEGER NOT NULL, 
        mukellef_id INTEGER NOT NULL, 
        belge_no TEXT NOT NULL, 
        
        -- Tarih ve Karar Bilgileri
        yukleme_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
        belge_tarihi TEXT,
        basvuru_tarihi TEXT,
        belge_alinma_tarihi TEXT,
        fiili_tamamlanma_tarihi TEXT,
        vize_basvuru_tarihi TEXT,
        ilk_indirim_yili INTEGER,
        karar TEXT,
        program_turu TEXT,
        yatirim_turu1 TEXT,
        yatirim_turu2 TEXT,
        vize_durumu TEXT,
        donem TEXT,
        il TEXT,
        osb TEXT,
        bolge TEXT,
        
        -- Oranlar ve Temel Tutarlar
        katki_orani REAL,
        vergi_orani REAL,
        diger_oran REAL,
        toplam_tutar REAL,
        
        -- Ara ve Önceki Dönem Hesaplama Verileri (Aşama 3 ve 4 verileri)
        katki_tutari REAL,
        diger_katki_tutari REAL,
        cari_harcama_tutari REAL,
        toplam_harcama_tutari REAL,
        fiili_katki_tutari REAL,
        endeks_katki_tutari REAL,
        onceki_yatirim_katki_tutari REAL,
        onceki_diger_katki_tutari REAL,
        onceki_katki_tutari REAL,
        
        -- Sonuç ve Dağılım Verileri (Aşama 7 ve Aşama 6)
        cari_yatirim_katki REAL DEFAULT 0.0,
        cari_diger_katki REAL DEFAULT 0.0,
        cari_toplam_katki REAL DEFAULT 0.0,
        genel_toplam_katki REAL DEFAULT 0.0,
        brut_satis REAL,
        ihracat REAL,
        imalat REAL,
        diger_faaliyet REAL,
        use_detailed_profit_ratios INTEGER DEFAULT 0,
        olusturan_id INTEGER,
        UNIQUE(user_id, mukellef_id, belge_no)
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




    # --- TEŞVİK KULLANIM TABLOSU (Doğru Sürüm - SQLite) ---
    c.execute("""
    CREATE TABLE IF NOT EXISTS tesvik_kullanim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        belge_no TEXT NOT NULL,
        hesap_donemi INTEGER NOT NULL,
        donem_turu TEXT DEFAULT 'KURUMLAR',

        -- 🔹 Kazanç Bilgileri
        yatirimdan_elde_edilen_kazanc REAL DEFAULT 0.0,
        tevsi_yatirim_kazanci REAL DEFAULT 0.0,
        diger_faaliyet REAL DEFAULT 0.0,

        -- 🔹 Cari Dönem Katkıları
        cari_yatirim_katki REAL DEFAULT 0.0,
        cari_diger_katki REAL DEFAULT 0.0,
        cari_toplam_katki REAL DEFAULT 0.0,

        -- 🔹 Genel ve Kalan Katkılar
        genel_toplam_katki REAL DEFAULT 0.0,
        kalan_katki_tutari REAL DEFAULT 0.0,

        -- 🔹 İndirimli KV Bilgileri
        indirimli_matrah REAL DEFAULT 0.0,
        indirimli_kv REAL DEFAULT 0.0,
        odenecek_toplam_kv REAL DEFAULT 0.0,
        indirimli_kv_oran REAL DEFAULT 0.0,

        -- 🔹 Sistem Alanı
        kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
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
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# --- USERS TABLOSU (PostgreSQL) ---
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_approved INTEGER DEFAULT 0,
    is_suspended INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    admin_notes TEXT
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
    vergi_dairesi TEXT,
    ilgili_memur TEXT,
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



cur.execute("""
CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
    id SERIAL PRIMARY KEY,
    
    -- Zorunlu İlişkiler ve Kimlikler
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mukellef_id INTEGER NOT NULL REFERENCES mukellef(id) ON DELETE CASCADE,
    belge_no TEXT NOT NULL, 
    
    -- Tarih ve Karar Bilgileri
    yukleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    belge_tarihi TEXT,
    basvuru_tarihi TEXT,
    belge_alinma_tarihi TEXT,
    fiili_tamamlanma_tarihi TEXT,
    vize_basvuru_tarihi TEXT,
    ilk_indirim_yili INTEGER,
    karar TEXT,
    program_turu TEXT,
    yatirim_turu1 TEXT,
    yatirim_turu2 TEXT,
    vize_durumu TEXT,
    donem TEXT,
    il TEXT,
    osb TEXT,
    bolge TEXT,
    
    -- Oranlar ve Temel Tutarlar
    katki_orani DOUBLE PRECISION,
    vergi_orani DOUBLE PRECISION,
    diger_oran DOUBLE PRECISION,
    toplam_tutar DOUBLE PRECISION,
    
    -- Ara ve Önceki Dönem Hesaplama Verileri
    katki_tutari DOUBLE PRECISION,
    diger_katki_tutari DOUBLE PRECISION,
    cari_harcama_tutari DOUBLE PRECISION,
    toplam_harcama_tutari DOUBLE PRECISION,
    fiili_katki_tutari DOUBLE PRECISION,
    endeks_katki_tutari DOUBLE PRECISION,
    onceki_yatirim_katki_tutari DOUBLE PRECISION,
    onceki_diger_katki_tutari DOUBLE PRECISION,
    onceki_katki_tutari DOUBLE PRECISION,
    
    -- Sonuç ve Dağılım Verileri
    cari_yatirim_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_diger_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
    genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
    brut_satis DOUBLE PRECISION,
    ihracat DOUBLE PRECISION,
    imalat DOUBLE PRECISION,
    diger_faaliyet DOUBLE PRECISION,
    use_detailed_profit_ratios BOOLEAN DEFAULT FALSE,
    olusturan_id INTEGER,    
    UNIQUE(user_id, mukellef_id, belge_no)
);
""")

# --- TEŞVİK KULLANIM TABLOSU (Doğru Sürüm - PostgreSQL) ---
cur.execute("""
CREATE TABLE IF NOT EXISTS tesvik_kullanim (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    belge_no TEXT NOT NULL,
    hesap_donemi INT NOT NULL,
    donem_turu TEXT DEFAULT 'KURUMLAR',

    -- 🔹 Kazanç Bilgileri
    yatirimdan_elde_edilen_kazanc DOUBLE PRECISION DEFAULT 0.0,
    tevsi_yatirim_kazanci DOUBLE PRECISION DEFAULT 0.0,
    diger_faaliyet DOUBLE PRECISION DEFAULT 0.0,

    -- 🔹 Cari Dönem Katkıları
    cari_yatirim_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_diger_katki DOUBLE PRECISION DEFAULT 0.0,
    cari_toplam_katki DOUBLE PRECISION DEFAULT 0.0,

    -- 🔹 Genel ve Kalan Katkılar
    genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
    kalan_katki_tutari DOUBLE PRECISION DEFAULT 0.0,

    -- 🔹 İndirimli KV Bilgileri
    indirimli_matrah DOUBLE PRECISION DEFAULT 0.0,
    indirimli_kv DOUBLE PRECISION DEFAULT 0.0,
    odenecek_toplam_kv DOUBLE PRECISION DEFAULT 0.0,
    indirimli_kv_oran DOUBLE PRECISION DEFAULT 0.0,

    -- 🔹 Sistem Alanı
    kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
);
""")

# --- İNDEKSLER ---
cur.execute("CREATE INDEX IF NOT EXISTS idx_mukellef_user ON mukellef(user_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_tesvik_user ON tesvik_belgeleri(user_id);")

conn.commit()
cur.close()
conn.close()

print("✅ PostgreSQL veritabanı başarıyla oluşturuldu (Supabase bağlantısı ile).")
