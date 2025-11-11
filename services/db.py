import os
import sqlite3
from psycopg2 import pool, extras
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 🌍 Ortam Algılama
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
DEBUG_MODE = (FLASK_ENV == "development") or (os.getenv("FLASK_DEBUG", "0") == "1")

USE_SQLITE = DATABASE_URL.startswith("sqlite:///") or (
    DEBUG_MODE and not DATABASE_URL.startswith("postgresql://")
)

if USE_SQLITE:
    DB_PATH = DATABASE_URL.replace("sqlite:///", "") or "instance/database.db"
    print(f"🧩 Yerel ortam algılandı — SQLite kullanılacak ({DB_PATH})")
else:
    print("☁️ Production ortam algılandı — Supabase PostgreSQL kullanılacak")

_db_pool = None



def get_pool():
    global _db_pool
    if _db_pool is None and not USE_SQLITE:
        _db_pool = pool.SimpleConnectionPool(
            1, 5,
            DATABASE_URL,
            connect_timeout=5,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            cursor_factory=extras.RealDictCursor
        )
        print("🔗 PostgreSQL bağlantı havuzu keepalive ile başlatıldı.")
    return _db_pool


# ============================================================
# 🧩 PostgreSQL-benzeri SQLite Wrapper
# ============================================================
class FakeCursor:
    def __init__(self, sqlite_cursor):
        self.sqlite_cursor = sqlite_cursor

    def execute(self, query, params=None):
        # PostgreSQL sözdizimini SQLite uyumlu hale getir
        q = query.replace("%s", "?")

        # 🔧 Ek düzeltmeler (SQLite ile tam uyumluluk)
        q = q.replace("NOW()", "CURRENT_TIMESTAMP")  # <-- HATAYI GİDERİR
        q = q.replace("ILIKE", "LIKE")               # case-insensitive aramalarda sorun çıkmasın
        q = q.replace("TRUE", "1").replace("FALSE", "0")

        self.sqlite_cursor.execute(q, params or ())

    def fetchall(self):
        return [dict(row) for row in self.sqlite_cursor.fetchall()]

    def fetchone(self):
        row = self.sqlite_cursor.fetchone()
        return dict(row) if row else None

    @property
    def description(self):
        if self.sqlite_cursor.description:
            return [(col[0],) for col in self.sqlite_cursor.description]
        return []

    @property
    def lastrowid(self):
        return self.sqlite_cursor.lastrowid

    def close(self):
        self.sqlite_cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()



class FakeConnection:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def cursor(self, *args, **kwargs):
        return FakeCursor(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


# ============================================================
# 🔒 get_conn() — Ortama Göre Bağlantı
# ============================================================
@contextmanager
def get_conn():
    """
    Ortama göre (SQLite veya PostgreSQL) bağlantı döndürür.
    PostgreSQL'de her cursor otomatik olarak RealDictCursor olur.
    """
    if USE_SQLITE:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = FakeConnection(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = get_pool().getconn()
        try:
            # ✅ Her cursor RealDictCursor olarak dönecek
            conn.cursor_factory = extras.RealDictCursor
            yield conn
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass  # bağlantı zaten kapanmış olabilir
            raise e
        finally:
            get_pool().putconn(conn)




# ============================================================
# 📚 Yardımcı Fonksiyonlar
# ============================================================
def fetch_all(query, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def execute(query, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
        conn.commit()


# ============================================================
# 🧱 migrate_* Fonksiyonları
# ============================================================
def migrate_users_table():
    """
    users tablosunu kontrol eder ve eksik sütunları ekler.
    Hem SQLite hem PostgreSQL için tam uyumludur.
    """
    with get_conn() as conn:
        cur = conn.cursor()

        try:
            # PostgreSQL ortamı
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE LOWER(table_name) = 'users';
            """)
            rows = cur.fetchall()
            # Bazı sürümler dict döner, bazıları tuple
            existing = {r["column_name"] if isinstance(r, dict) else r[0] for r in rows}
        except Exception:
            # SQLite ortamı
            cur.execute("PRAGMA table_info(users);")
            rows = cur.fetchall()
            existing = {r["name"] if isinstance(r, dict) else r[1] for r in rows}

        # Eksik kolonlar
        columns_to_add = [
            ("is_approved", "INTEGER DEFAULT 0"),
            ("is_suspended", "INTEGER DEFAULT 0"),
            ("role", "TEXT DEFAULT 'user'"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("last_login", "TIMESTAMP NULL"),
            ("admin_notes", "TEXT NULL"),
        ]

        # Sütunları sırayla kontrol et ve ekle
        for name, definition in columns_to_add:
            if name not in existing:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {name} {definition};")
                    print(f"🆕 '{name}' sütunu eklendi.")
                except Exception as e:
                    # Eğer zaten varsa ya da ALTER TABLE kısıtı varsa sessiz geç
                    print(f"⚠️ '{name}' sütunu eklenemedi veya zaten mevcut: {e}")

        conn.commit()
        print("✅ users tablosu kontrol edildi / güncellendi.")




def migrate_login_logs_table():
    with get_conn() as conn:
        c = conn.cursor()
        if USE_SQLITE:
            c.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                ip_address TEXT,
                user_agent TEXT,
                login_time TEXT DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 1
            );
            """)
        else:
            c.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                username TEXT,
                ip_address TEXT,
                user_agent TEXT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE
            );
            """)
        conn.commit()
        print("✅ login_logs tablosu kontrol edildi / oluşturuldu.")


def migrate_tesvik_columns():
    """tesvik_belgeleri tablosuna eksik sütunları ekler."""
    with get_conn() as conn:
        cur = conn.cursor()

        if USE_SQLITE:
            cur.execute("PRAGMA table_info(tesvik_belgeleri)")
            existing = {r["name"] for r in cur.fetchall()}
        else:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tesvik_belgeleri'")
            existing = {r["column_name"] for r in cur.fetchall()}

        to_add = {
            "yukleme_tarihi": "TEXT",
            "belge_no": "TEXT",
            "belge_tarihi": "TEXT",
            "karar": "TEXT",
            "yatirim_turu1": "TEXT",
            "yatirim_turu2": "TEXT",
            "program_turu": "TEXT",
            "vize_durumu": "TEXT",
            "donem": "TEXT",
            "il": "TEXT",
            "osb": "TEXT",
            "bolge": "TEXT",
            "katki_orani": "REAL",
            "vergi_orani": "REAL",
            "diger_oran": "REAL",
            "toplam_tutar": "REAL",
            "katki_tutari": "REAL",
            "diger_katki_tutari": "REAL",
            "cari_harcama_tutari": "REAL",
            "toplam_harcama_tutari": "REAL",
            "fiili_katki_tutari": "REAL",
            "endeks_katki_tutari": "REAL",
            "onceki_yatirim_katki_tutari": "REAL",
            "onceki_diger_katki_tutari": "REAL",
            "onceki_katki_tutari": "REAL",
            "cari_yatirim_katki": "REAL",
            "cari_diger_katki": "REAL",
            "cari_toplam_katki": "REAL",
            "genel_toplam_katki": "REAL",
            "brut_satis": "REAL",
            "ihracat": "REAL",
            "imalat": "REAL",
            "diger_faaliyet": "REAL",
            "use_detailed_profit_ratios": "INTEGER DEFAULT 0",
            "olusturan_id": "INTEGER"
            
        }

        for col, col_type in to_add.items():
            if col not in existing:
                print(f"🆕 '{col}' sütunu ekleniyor...")
                cur.execute(f'ALTER TABLE tesvik_belgeleri ADD COLUMN "{col}" {col_type}')

        conn.commit()
        print("✅ tesvik_belgeleri tablosu güncel.")


def migrate_tesvik_kullanim_table():
    """tesvik_kullanim tablosunu oluşturur (yoksa) ve eksik sütunları ekler."""
    with get_conn() as conn:
        cur = conn.cursor()

        # -------------------------------
        # 🔹 SQLite Ortamı
        # -------------------------------
        if USE_SQLITE:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tesvik_kullanim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                belge_no TEXT NOT NULL,
                hesap_donemi INTEGER NOT NULL,
                donem_turu TEXT DEFAULT 'KURUMLAR',
                yatirim_kazanci REAL DEFAULT 0.0,
                diger_kazanc REAL DEFAULT 0.0,
                cari_yatirim_katkisi REAL DEFAULT 0.0,
                cari_diger_katkisi REAL DEFAULT 0.0,
                genel_toplam_katki REAL DEFAULT 0.0,
                kalan_katki REAL DEFAULT 0.0,
                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
            );
            """)
        # -------------------------------
        # 🔹 PostgreSQL Ortamı
        # -------------------------------
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tesvik_kullanim (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                belge_no TEXT NOT NULL,
                hesap_donemi INT NOT NULL,
                donem_turu TEXT DEFAULT 'KURUMLAR',
                yatirim_kazanci DOUBLE PRECISION DEFAULT 0.0,
                diger_kazanc DOUBLE PRECISION DEFAULT 0.0,
                cari_yatirim_katkisi DOUBLE PRECISION DEFAULT 0.0,
                cari_diger_katkisi DOUBLE PRECISION DEFAULT 0.0,
                genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
                kalan_katki DOUBLE PRECISION DEFAULT 0.0,
                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
            );
            """)

        # 🔍 Eğer mevcut tablo eskiyse ve `donem_turu` sütunu yoksa ekle
        try:
            if USE_SQLITE:
                cur.execute("PRAGMA table_info(tesvik_kullanim)")
                existing = {r["name"] for r in cur.fetchall()}
            else:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tesvik_kullanim'")
                existing = {r["column_name"] for r in cur.fetchall()}

            if "donem_turu" not in existing:
                cur.execute("ALTER TABLE tesvik_kullanim ADD COLUMN donem_turu TEXT DEFAULT 'KURUMLAR';")
                print("🆕 'donem_turu' sütunu eklendi.")
        except Exception as e:
            print(f"⚠️ donem_turu sütunu kontrolü sırasında hata: {e}")

        conn.commit()
        print("✅ tesvik_kullanim tablosu kontrol edildi / oluşturuldu.")




def migrate_profit_data_table():
    """profit_data tablosuna (user_id, aciklama_index) için benzersiz kısıt ekler.
    Hem SQLite hem PostgreSQL için uyumlu çalışır.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            if USE_SQLITE:
                # SQLite ortamı
                cur.execute("PRAGMA table_info(profit_data)")
                existing_cols = {r["name"] for r in cur.fetchall()}

                # Eğer tablo yoksa oluştur
                if not existing_cols:
                    print("🆕 profit_data tablosu oluşturuluyor (SQLite)...")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS profit_data (
                            user_id INTEGER NOT NULL,
                            aciklama_index INTEGER NOT NULL,
                            column_b REAL,
                            column_c REAL,
                            column_d REAL,
                            column_e REAL,
                            PRIMARY KEY (user_id, aciklama_index)
                        );
                    """)
                    print("✅ profit_data tablosu oluşturuldu.")
                else:
                    # Tablo varsa, PRIMARY KEY yoksa yeniden oluştur
                    cur.execute("""
                        SELECT sql FROM sqlite_master 
                        WHERE type='table' AND name='profit_data';
                    """)
                    table_sql = cur.fetchone()
                    if table_sql and "PRIMARY KEY" not in str(table_sql["sql"]).upper():
                        print("🛠️ SQLite: PRIMARY KEY ekleniyor (profit_data)...")
                        cur.execute("PRAGMA foreign_keys=off;")
                        cur.execute("""
                            CREATE TABLE profit_data_new (
                                user_id INTEGER NOT NULL,
                                aciklama_index INTEGER NOT NULL,
                                column_b REAL,
                                column_c REAL,
                                column_d REAL,
                                column_e REAL,
                                PRIMARY KEY (user_id, aciklama_index)
                            );
                        """)
                        cur.execute("""
                            INSERT OR IGNORE INTO profit_data_new
                            SELECT user_id, aciklama_index, column_b, column_c, column_d, column_e
                            FROM profit_data;
                        """)
                        cur.execute("DROP TABLE profit_data;")
                        cur.execute("ALTER TABLE profit_data_new RENAME TO profit_data;")
                        cur.execute("PRAGMA foreign_keys=on;")
                        print("✅ SQLite: PRIMARY KEY (user_id, aciklama_index) eklendi.")
                    else:
                        print("✅ profit_data tablosu zaten güncel (SQLite).")

            else:
                # PostgreSQL ortamı
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'profit_data_user_idx_unique'
                        ) THEN
                            ALTER TABLE profit_data
                            ADD CONSTRAINT profit_data_user_idx_unique
                            UNIQUE (user_id, aciklama_index);
                        END IF;
                    END$$;
                """)
                print("✅ PostgreSQL: UNIQUE constraint kontrol edildi / eklendi.")

            conn.commit()
        except Exception as e:
            print(f"⚠️ migrate_profit_data_table hatası: {e}")
