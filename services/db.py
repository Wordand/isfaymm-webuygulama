import os
from psycopg2 import pool, extras
from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL bağlantı havuzu ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL bulunamadı. Render Environment ayarını kontrol et.")

# Bağlantı havuzu (1–10 arası aktif bağlantı tutar)
db_pool = pool.SimpleConnectionPool(
    1, 10, DATABASE_URL, cursor_factory=extras.RealDictCursor
)

def get_conn():
    """
    Havuzdan bir bağlantı alır.
    Her sorguda yeniden bağlantı açmak yerine bu havuzu kullanır.
    """
    global db_pool  # ✅ global tanımı fonksiyonun başında olmalı

    try:
        return db_pool.getconn()
    except Exception:
        # Hatalı bağlantı olursa havuzu yeniden kur
        db_pool = pool.SimpleConnectionPool(1, 10, DATABASE_URL, cursor_factory=extras.RealDictCursor)
        return db_pool.getconn()

def put_conn(conn):
    """
    Kullanım bittiğinde bağlantıyı havuza geri verir.
    (Normalde 'with' kullanılmazsa manuel çağrılabilir.)
    """
    if conn:
        db_pool.putconn(conn)




def migrate_tesvik_columns():
    """
    tesvik_belgeleri tablosunda eksik sütunları kontrol eder ve ekler.
    PostgreSQL için uygun hale getirilmiştir.
    """
    with get_conn() as conn:
        cur = conn.cursor()

        # Mevcut sütun adlarını al
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tesvik_belgeleri';
        """)
        existing = {row['column_name'] for row in cur.fetchall()}

        to_add = {
            "belge_no":                   "TEXT",
            "belge_tarihi":               "TEXT",
            "karar":                      "TEXT",
            "yatirim_turu1":              "TEXT",
            "yatirim_turu2":              "TEXT",
            "toplam_tutar":               "DOUBLE PRECISION",
            "katki_orani":                "DOUBLE PRECISION",
            "vergi_orani":                "DOUBLE PRECISION",
            "bolge":                      "TEXT",
            "diger_oran":                 "DOUBLE PRECISION",
            "katki_tutari":               "DOUBLE PRECISION",
            "cari_harcama_tutari":        "DOUBLE PRECISION",
            "toplam_harcama_tutari":      "DOUBLE PRECISION",
            "fiili_katki_tutari":         "DOUBLE PRECISION",
            "endeks_katki_tutari":        "DOUBLE PRECISION",
            "onceki_yatirim_katki_tutari":"DOUBLE PRECISION",
            "onceki_diger_katki_tutari":  "DOUBLE PRECISION",
            "onceki_katki_tutari":        "DOUBLE PRECISION",
            "cari_yatirim_katki":         "DOUBLE PRECISION",
            "cari_diger_katki":           "DOUBLE PRECISION",
            "cari_toplam_katki":          "DOUBLE PRECISION",
            "genel_toplam_katki":         "DOUBLE PRECISION"
        }

        for col, col_type in to_add.items():
            if col not in existing:
                print(f"🆕 '{col}' sütunu ekleniyor...")
                cur.execute(f'ALTER TABLE tesvik_belgeleri ADD COLUMN "{col}" {col_type};')

        # Belgeler tablosu oluşturulmamışsa oluştur
        cur.execute("""
        CREATE TABLE IF NOT EXISTS belgeler (
            id SERIAL PRIMARY KEY,
            unvan TEXT NOT NULL,
            donem TEXT NOT NULL,
            belge_adi TEXT NOT NULL,
            belge_turu TEXT NOT NULL,
            dosya_yolu TEXT NOT NULL,
            yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        print("✅ migrate_tesvik_columns tamamlandı.")


def migrate_users_table():
    """
    users tablosunda 'is_approved' sütunu yoksa ekler.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users';
        """)
        existing = {row['column_name'] for row in cur.fetchall()}

        if "is_approved" not in existing:
            print("🛠️ 'is_approved' sütunu users tablosuna ekleniyor...")
            cur.execute('ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 0;')
            conn.commit()
            print("✅ 'is_approved' sütunu başarıyla eklendi.")
        else:
            print("✅ 'is_approved' sütunu zaten mevcut.")
