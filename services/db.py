import os
import sqlite3
from psycopg2 import pool, extras
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Ortam Algilama
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
DEBUG_MODE = (FLASK_ENV == "development") or (os.getenv("FLASK_DEBUG", "0") == "1")

USE_SQLITE = DATABASE_URL.startswith("sqlite:///") or (
    DEBUG_MODE and not DATABASE_URL.startswith("postgresql://")
)

if USE_SQLITE:
    DB_PATH = DATABASE_URL.replace("sqlite:///", "") or "instance/database.db"
    print(f"Yerel ortam algılandı - SQLite kullanılacak ({DB_PATH})")
else:
    print("Production ortamı algılandı - PostgreSQL kullanılacak")

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
        print("PostgreSQL baglanti havuzu baslatildi.")
    return _db_pool


# ============================================================
# PostgreSQL-benzeri SQLite Wrapper
# ============================================================
class FakeCursor:
    def __init__(self, sqlite_cursor):
        self.sqlite_cursor = sqlite_cursor

    def execute(self, query, params=None):
        # PostgreSQL sözdizimini SQLite uyumlu hale getir
        q = query.replace("%s", "?")

        # Ek duzeltmeler (SQLite ile tam uyumluluk)
        q = q.replace("NOW()", "CURRENT_TIMESTAMP")
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
# get_conn() - Ortama Gore Baglanti
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
# Yardimci Fonksiyonlar
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
# migrate_* Fonksiyonlari
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
            ("has_kdv_access", "INTEGER DEFAULT 0"),
            ("kdv_pin", "TEXT DEFAULT '1234'"),
        ]

        # Sütunları sırayla kontrol et ve ekle
        for name, definition in columns_to_add:
            if name not in existing:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {name} {definition};")
                    print(f"'{name}' sutunu eklendi.")
                except Exception as e:
                    # Eger zaten varsa sessiz gec
                    print(f"'{name}' sutunu eklenemedi: {e}")

        conn.commit()
    print("Users tablosu kontrol edildi.")

# Removed redundant migrate_kdv_assignments_table

def migrate_mukellef_table():
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            # PostgreSQL
            cur.execute("SELECT column_name FROM information_schema.columns WHERE LOWER(table_name) = 'mukellef';")
            rows = cur.fetchall()
            existing = {r["column_name"] if isinstance(r, dict) else r[0] for r in rows}
        except Exception:
            # SQLite
            cur.execute("PRAGMA table_info(mukellef);")
            rows = cur.fetchall()
            existing = {r["name"] if isinstance(r, dict) else r[1] for r in rows}

        columns = [
            ("vergi_dairesi", "TEXT NULL"),
            ("ilgili_memur", "TEXT NULL")
        ]

        for name, definition in columns:
            if name not in existing:
                try:
                    cur.execute(f"ALTER TABLE mukellef ADD COLUMN {name} {definition};")
                    print(f"'{name}' sutunu eklendi.")
                except Exception as e:
                    print(f"'{name}' sutunu eklenemedi: {e}")
        conn.commit()
    print("Mukellef tablosu kontrol edildi.")




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
        print("Login_logs tablosu kontrol edildi.")


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
            "olusturan_id": "INTEGER" if USE_SQLITE else "INTEGER"
            
        }

        for col, col_type in to_add.items():
            if col not in existing:
                print(f"'{col}' sutunu ekleniyor...")
                cur.execute(f'ALTER TABLE tesvik_belgeleri ADD COLUMN "{col}" {col_type}')

        conn.commit()
        print("Tesvik_belgeleri tablosu guncel.")

def migrate_tesvik_kullanim_table():
    """
    tesvik_kullanim tablosunu oluşturur veya eksik sütunları ekler.
    Güncel alan isimleri: yatirimdan_elde_edilen_kazanc, tevsi_yatirim_kazanci, diger_faaliyet, vb.
    Hem SQLite hem PostgreSQL ortamlarıyla uyumludur.
    """
    with get_conn() as conn:
        cur = conn.cursor()

        # ===========================
        # Tablo Olusturma Blogu
        # ===========================
        if USE_SQLITE:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tesvik_kullanim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                belge_no TEXT NOT NULL,
                hesap_donemi INTEGER NOT NULL,
                donem_turu TEXT DEFAULT 'KURUMLAR',

                yatirimdan_elde_edilen_kazanc REAL DEFAULT 0.0,
                tevsi_yatirim_kazanci REAL DEFAULT 0.0,
                diger_faaliyet REAL DEFAULT 0.0,

                cari_yatirim_katki REAL DEFAULT 0.0,
                cari_diger_katki REAL DEFAULT 0.0,
                cari_toplam_katki REAL DEFAULT 0.0,

                genel_toplam_katki REAL DEFAULT 0.0,
                kalan_katki_tutari REAL DEFAULT 0.0,

                indirimli_matrah REAL DEFAULT 0.0,
                indirimli_kv REAL DEFAULT 0.0,
                indirimli_kv_oran REAL DEFAULT 0.0,

                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
            );
            """)
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tesvik_kullanim (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                belge_no TEXT NOT NULL,
                hesap_donemi INT NOT NULL,
                donem_turu TEXT DEFAULT 'KURUMLAR',

                yatirimdan_elde_edilen_kazanc DOUBLE PRECISION DEFAULT 0.0,
                tevsi_yatirim_kazanci DOUBLE PRECISION DEFAULT 0.0,
                diger_faaliyet DOUBLE PRECISION DEFAULT 0.0,

                cari_yatirim_katki DOUBLE PRECISION DEFAULT 0.0,
                cari_diger_katki DOUBLE PRECISION DEFAULT 0.0,
                cari_toplam_katki DOUBLE PRECISION DEFAULT 0.0,

                genel_toplam_katki DOUBLE PRECISION DEFAULT 0.0,
                kalan_katki_tutari DOUBLE PRECISION DEFAULT 0.0,

                indirimli_matrah DOUBLE PRECISION DEFAULT 0.0,
                indirimli_kv DOUBLE PRECISION DEFAULT 0.0,
                indirimli_kv_oran DOUBLE PRECISION DEFAULT 0.0,

                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, belge_no, hesap_donemi, donem_turu)
            );
            """)

        # ===========================
        # Eksik Sutun Kontrolu
        # ===========================
        try:
            if USE_SQLITE:
                cur.execute("PRAGMA table_info(tesvik_kullanim)")
                existing_cols = {r["name"] if isinstance(r, dict) else r[1] for r in cur.fetchall()}
            else:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'tesvik_kullanim';
                """)
                existing_cols = {r["column_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()}

            required_cols = [
                "yatirimdan_elde_edilen_kazanc", "tevsi_yatirim_kazanci", "diger_faaliyet",
                "cari_yatirim_katki", "cari_diger_katki", "cari_toplam_katki",
                "genel_toplam_katki", "kalan_katki_tutari",
                "indirimli_matrah", "indirimli_kv", "indirimli_kv_oran"
            ]

            for col in required_cols:
                if col not in existing_cols:
                    col_type = "REAL" if USE_SQLITE else "DOUBLE PRECISION"
                    cur.execute(f"ALTER TABLE tesvik_kullanim ADD COLUMN {col} {col_type} DEFAULT 0.0;")
                    print(f"'{col}' sutunu eklendi.")

        except Exception as e:
            print(f"Eksik sutun kontrolu hatasi: {e}")

        # ===========================
        # Unique Constraint
        # ===========================
        if not USE_SQLITE:
            try:
                cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'tesvik_kullanim_unique'
                    ) THEN
                        ALTER TABLE tesvik_kullanim
                        ADD CONSTRAINT tesvik_kullanim_unique
                        UNIQUE (user_id, belge_no, hesap_donemi, donem_turu);
                    END IF;
                END $$;
                """)
                print("UNIQUE constraint kontrol edildi.")
            except Exception as e:
                print(f"UNIQUE constraint hatasi: {e}")

        conn.commit()
        print("Tesvik_kullanim tablosu kontrol edildi.")




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
                    print("Profit_data tablosu olusturuluyor...")
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
                    print("Profit_data tablosu olusturuldu.")
                else:
                    # Tablo varsa, PRIMARY KEY yoksa yeniden oluştur
                    cur.execute("""
                        SELECT sql FROM sqlite_master 
                        WHERE type='table' AND name='profit_data';
                    """)
                    table_sql = cur.fetchone()
                    if table_sql and "PRIMARY KEY" not in str(table_sql["sql"]).upper():
                        print("SQLite: PRIMARY KEY ekleniyor...")
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
                        print("SQLite: PRIMARY KEY (user_id, aciklama_index) eklendi.")
                    else:
                        print("Profit_data tablosu zaten guncel.")

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
                print("PostgreSQL: UNIQUE constraint kontrol edildi.")

            conn.commit()
        except Exception as e:
            print(f"Migrate_profit_data_table hatasi: {e}")

def migrate_kdv_mukellef_table():
    """KDV Portalı için ayrıştırılmış mükellef tablosu."""
    with get_conn() as conn:
        cur = conn.cursor()
        if USE_SQLITE:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_mukellef (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vkn TEXT UNIQUE NOT NULL,
                unvan TEXT NOT NULL,
                vergi_dairesi TEXT,
                ilgili_memur TEXT,
                sektor TEXT,
                adres TEXT,
                yetkili_ad_soyad TEXT,
                yetkili_tel TEXT,
                yetkili_eposta TEXT,
                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_mukellef (
                id SERIAL PRIMARY KEY,
                vkn TEXT UNIQUE NOT NULL,
                unvan TEXT NOT NULL,
                vergi_dairesi TEXT,
                ilgili_memur TEXT,
                sektor TEXT,
                adres TEXT,
                yetkili_ad_soyad TEXT,
                yetkili_tel TEXT,
                yetkili_eposta TEXT,
                kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        conn.commit()
    print("kdv_mukellef tablosu kontrol edildi.")



def migrate_kdv_tables():
    """KDV takip sistemi için gerekli tabloları oluşturur."""
    with get_conn() as conn:
        cur = conn.cursor()

        if not USE_SQLITE:
            # PostgreSQL Foreign Key Duzeltmesi (Eski mükellef tablosuna referans varsa kdv_mukellef'e çevir)
            try:
                # kdv_files FK fix
                cur.execute("ALTER TABLE kdv_files DROP CONSTRAINT IF EXISTS kdv_files_mukellef_id_fkey;")
                cur.execute("ALTER TABLE kdv_files ADD CONSTRAINT kdv_files_mukellef_id_fkey FOREIGN KEY (mukellef_id) REFERENCES kdv_mukellef(id) ON DELETE CASCADE;")
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"kdv_files FK fix skip: {e}")

        # Check for amount_guarantee column
        try:
            if USE_SQLITE:
                cur.execute("PRAGMA table_info(kdv_files)")
                cols = {r["name"] for r in cur.fetchall()}
            else:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='kdv_files'")
                cols = {r["column_name"] for r in cur.fetchall()}
            
            if "amount_guarantee" not in cols:
                print("Adding amount_guarantee column to kdv_files...")
                if USE_SQLITE:
                    cur.execute("ALTER TABLE kdv_files ADD COLUMN amount_guarantee REAL DEFAULT 0")
                else:
                    cur.execute("ALTER TABLE kdv_files ADD COLUMN amount_guarantee DOUBLE PRECISION DEFAULT 0")
                conn.commit()
        except Exception as e:
            print(f"Migration error for amount_guarantee: {e}")


            try:
                # kdv_bank_guarantees fix
                cur.execute("ALTER TABLE kdv_bank_guarantees DROP CONSTRAINT IF EXISTS kdv_bank_guarantees_mukellef_id_fkey;")
                cur.execute("ALTER TABLE kdv_bank_guarantees ADD CONSTRAINT kdv_bank_guarantees_mukellef_id_fkey FOREIGN KEY (mukellef_id) REFERENCES kdv_mukellef(id) ON DELETE CASCADE;")
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"kdv_bank_guarantees FK fix skip: {e}")

        if USE_SQLITE:
            # KDV Dosyaları
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mukellef_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                period TEXT NOT NULL,
                subject TEXT NOT NULL,
                type TEXT NOT NULL,
                amount_request REAL DEFAULT 0,
                amount_tenzil REAL DEFAULT 0,
                amount_bloke REAL DEFAULT 0,
                amount_resolved REAL DEFAULT 0,
                status TEXT NOT NULL,
                location TEXT,
                date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_guaranteed INTEGER DEFAULT 0,
                guarantee_date TEXT,
                FOREIGN KEY (mukellef_id) REFERENCES kdv_mukellef(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            # Dosya İşlem Geçmişi (Timeline)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                text TEXT NOT NULL,
                description TEXT,
                file_name TEXT,
                FOREIGN KEY (file_id) REFERENCES kdv_files(id) ON DELETE CASCADE
            );
            """)

            # Banka Teminat Mektupları
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_bank_guarantees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mukellef_id INTEGER NOT NULL,
                file_id INTEGER,
                bank TEXT NOT NULL,
                amount REAL NOT NULL,
                expiry_date TEXT NOT NULL,
                status TEXT DEFAULT 'Aktif',
                FOREIGN KEY (mukellef_id) REFERENCES kdv_mukellef(id) ON DELETE CASCADE,
                FOREIGN KEY (file_id) REFERENCES kdv_files(id) ON DELETE SET NULL
            );
            """)

            # KDV Belgeleri (Versiyonlama için)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                file_path TEXT,
                parent_id INTEGER,
                version INTEGER DEFAULT 1,
                FOREIGN KEY (file_id) REFERENCES kdv_files(id) ON DELETE CASCADE
            );
            """)

            # KDV Atamaları (User <-> KDV Mukellef)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_user_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mukellef_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, mukellef_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (mukellef_id) REFERENCES kdv_mukellef(id) ON DELETE CASCADE
            );
            """)
        else:
            # PostgreSQL
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_files (
                id SERIAL PRIMARY KEY,
                mukellef_id INTEGER NOT NULL REFERENCES kdv_mukellef(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                period TEXT NOT NULL,
                subject TEXT NOT NULL,
                type TEXT NOT NULL,
                amount_request DOUBLE PRECISION DEFAULT 0,
                amount_tenzil DOUBLE PRECISION DEFAULT 0,
                amount_bloke DOUBLE PRECISION DEFAULT 0,
                amount_resolved DOUBLE PRECISION DEFAULT 0,
                status TEXT NOT NULL,
                location TEXT,
                date TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_guaranteed BOOLEAN DEFAULT FALSE,
                guarantee_date TEXT
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_history (
                id SERIAL PRIMARY KEY,
                file_id INTEGER NOT NULL REFERENCES kdv_files(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                text TEXT NOT NULL,
                description TEXT,
                file_name TEXT
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_bank_guarantees (
                id SERIAL PRIMARY KEY,
                mukellef_id INTEGER NOT NULL REFERENCES kdv_mukellef(id) ON DELETE CASCADE,
                file_id INTEGER REFERENCES kdv_files(id) ON DELETE SET NULL,
                bank TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                expiry_date TEXT NOT NULL,
                status TEXT DEFAULT 'Aktif'
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_documents (
                id SERIAL PRIMARY KEY,
                file_id INTEGER NOT NULL REFERENCES kdv_files(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                file_path TEXT,
                parent_id INTEGER,
                version INTEGER DEFAULT 1
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_user_assignments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mukellef_id INTEGER NOT NULL REFERENCES kdv_mukellef(id) ON DELETE CASCADE,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, mukellef_id)
            );
            """)

        conn.commit()
    print("KDV tablolari kontrol edildi.")

def migrate_kdv_documents_table():
    """kdv_documents tablosuna eksik sütunları ekler."""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            if USE_SQLITE:
                cur.execute("PRAGMA table_info(kdv_documents)")
                existing = {r["name"] for r in cur.fetchall()}
            else:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='kdv_documents'")
                existing = {r["column_name"] for r in cur.fetchall()}

            if "file_path" not in existing:
                print("'file_path' sutunu kdv_documents tablosuna ekleniyor...")
                cur.execute('ALTER TABLE kdv_documents ADD COLUMN file_path TEXT')
                conn.commit()
        except Exception as e:
            print(f"migrate_kdv_documents_table hatasi: {e}")

def migrate_kdv_notes_table():
    """KDV dosyaları için hızlı bilgi/notlar tablosunu oluşturur."""
    with get_conn() as conn:
        cur = conn.cursor()
        if USE_SQLITE:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (file_id) REFERENCES kdv_files(id) ON DELETE CASCADE
            );
            """)
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS kdv_notes (
                id SERIAL PRIMARY KEY,
                file_id INTEGER NOT NULL REFERENCES kdv_files(id) ON DELETE CASCADE,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            """)
        conn.commit()
    print("kdv_notes tablosu kontrol edildi.")
