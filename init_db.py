import sqlite3
import os

# init_db.py dosyasının bulunduğu dizin
base_dir = os.path.dirname(os.path.abspath(__file__))
# instance klasörünün yolu
instance_path = os.path.join(base_dir, 'instance')
# database.db dosyasının tam yolu
database_path = os.path.join(instance_path, 'database.db')

# instance klasörünün var olduğundan emin ol
os.makedirs(instance_path, exist_ok=True)

conn = sqlite3.connect(database_path)
c = conn.cursor()

# Kullanıcılar tablosu (şifreler HASH olarak saklanmalı)
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL   -- ⚠️ HASH olarak saklanmalı, plain-text değil!
)
''')

# Matrahlar tablosu
c.execute('''
CREATE TABLE IF NOT EXISTS matrahlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gelir REAL,
    gider REAL,
    matrah REAL,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

# Mükellef tablosu
c.execute('''
CREATE TABLE IF NOT EXISTS mukellef (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vergi_kimlik_no TEXT NOT NULL,
    unvan TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, vergi_kimlik_no)
)
''')

# Beyanname tablosu
c.execute('''
CREATE TABLE IF NOT EXISTS beyanname (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mukellef_id INTEGER NOT NULL,
    donem TEXT NOT NULL,
    tur TEXT NOT NULL,
    veriler TEXT,
    dosya_adi TEXT,
    yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(mukellef_id) REFERENCES mukellef(id) ON DELETE CASCADE,
    UNIQUE(user_id, mukellef_id, donem, tur)
)
''')

# Teşvik belgeleri tablosu
c.execute('''
CREATE TABLE IF NOT EXISTS tesvik_belgeleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dosya_adi TEXT NOT NULL,
    yukleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Kimlik ve tarih bilgileri
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

    -- Oranlar
    katki_orani REAL,
    vergi_orani REAL,
    diger_oran REAL,

    -- Yatırım tutar bilgileri
    toplam_tutar REAL,
    katki_tutari REAL,
    diger_katki_tutari REAL,
    cari_harcama_tutari REAL,
    toplam_harcama_tutari REAL,
    fiili_katki_tutari REAL,
    endeks_katki_tutari REAL,

    -- Önceki dönemlerden gelen
    onceki_yatirim_katki_tutari REAL,
    onceki_diger_katki_tutari REAL,
    onceki_katki_tutari REAL,

    -- Cari ve genel toplam katkılar
    cari_yatirim_katki REAL DEFAULT 0.0,
    cari_diger_katki REAL DEFAULT 0.0,
    cari_toplam_katki REAL DEFAULT 0.0,
    genel_toplam_katki REAL DEFAULT 0.0,

    -- Satış ve Faaliyet Dağılımı
    brut_satis REAL,
    ihracat REAL,
    imalat REAL,
    diger_faaliyet REAL,
    use_detailed_profit_ratios BOOLEAN DEFAULT FALSE,

    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
''')

# Profit data tablosu
c.execute('''
CREATE TABLE IF NOT EXISTS profit_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    aciklama_index INTEGER NOT NULL,
    column_b REAL DEFAULT 0.0,
    column_c REAL DEFAULT 0.0,
    column_d REAL DEFAULT 0.0,
    column_e REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, aciklama_index)
)
''')

# Performans için indexler
c.execute("CREATE INDEX IF NOT EXISTS idx_mukellef_user ON mukellef(user_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_beyanname_user ON beyanname(user_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_tesvik_user ON tesvik_belgeleri(user_id)")

# Veritabanı işlemlerini kaydet ve kapat
conn.commit()

print("✅ Veritabanı başarıyla oluşturuldu:", database_path)

conn.close()
