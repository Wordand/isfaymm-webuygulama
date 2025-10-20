import sqlite3
from flask import current_app

def get_conn():
    """
    Uygulamanın config'indeki DATABASE yoluna bağlanır,
    sqlite3.Row kullanarak kolon isimleriyle erişimi sağlar.
    """
    db_path = current_app.config.get("DATABASE", "database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_tesvik_columns():
    """
    tesvik_belgeleri tablosuna eksik sütunları ekler.
    CREATE TABLE IF NOT EXISTS çalıştıktan sonra çağrılmalı.
    """
    with get_conn() as conn:
        c = conn.cursor()
        # Mevcut sütun adlarını al
        c.execute("PRAGMA table_info(tesvik_belgeleri)")
        existing = {row[1] for row in c.fetchall()}

        # Şablonda kullandığın tüm alanlar:
        to_add = {
            "belge_no":                   "TEXT",
            "belge_tarihi":               "TEXT",
            "karar":                      "TEXT",
            "yatirim_turu1":              "TEXT",
            "yatirim_turu2":              "TEXT",
            "toplam_tutar":               "REAL",
            "katki_orani":                "REAL",
            "vergi_orani":                "REAL",
            "bolge":                      "TEXT",
            "diger_oran":                 "REAL",
            "katki_tutari":               "REAL",
            "cari_harcama_tutari":        "REAL",
            "toplam_harcama_tutari":      "REAL",
            "fiili_katki_tutari":         "REAL",
            "endeks_katki_tutari":        "REAL",
            "onceki_yatirim_katki_tutari":"REAL",
            "onceki_diger_katki_tutari":  "REAL",
            "onceki_katki_tutari":        "REAL",
            "cari_yatirim_katki":         "REAL",
            "cari_diger_katki":           "REAL",
            "cari_toplam_katki":          "REAL",
            "genel_toplam_katki":         "REAL"
        }

        for col, col_type in to_add.items():
            if col not in existing:
                c.execute(f"ALTER TABLE tesvik_belgeleri ADD COLUMN {col} {col_type}")

        c.execute('''
        CREATE TABLE IF NOT EXISTS belgeler (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            unvan           TEXT    NOT NULL,
            donem           TEXT    NOT NULL,
            belge_adi       TEXT    NOT NULL,
            belge_turu      TEXT    NOT NULL,
            dosya_yolu      TEXT    NOT NULL,
            yuklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()


# 🆕 Yeni eklenecek fonksiyon:
def migrate_users_table():
    """
    users tablosunda 'is_approved' sütunu yoksa ekler.
    Bu sütun, admin onayı sisteminde kullanılır.
    """
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in c.fetchall()}

        if "is_approved" not in existing:
            print("🛠️ 'is_approved' sütunu users tablosuna ekleniyor...")
            c.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 0")
            conn.commit()
            print("✅ 'is_approved' sütunu başarıyla eklendi.")
        else:
            print("✅ 'is_approved' sütunu zaten mevcut.")
