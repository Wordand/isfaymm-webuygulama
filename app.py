from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from flask import Flask, session
from flask_limiter import Limiter
from werkzeug.security import generate_password_hash
from jinja2 import Undefined
import os
from datetime import timedelta

# Custom Modules
import config
from extensions import limiter, fernet
from services.db import (
    migrate_users_table, migrate_login_logs_table, migrate_tesvik_columns, 
    migrate_tesvik_kullanim_table, migrate_profit_data_table, migrate_kdv_tables,
    migrate_mukellef_table, migrate_kdv_mukellef_table, migrate_kdv_documents_table,
    migrate_kdv_notes_table, get_conn
)
from services.utils import safe_date, currency_filter, tlformat

# Blueprints
from routes.main_routes import bp as main_bp
from routes.auth_routes import bp as auth_bp
from routes.admin_routes import bp as admin_bp
from routes.data_routes import bp as data_bp
from routes.report_routes import bp as report_bp
from routes.tools_routes import bp as tools_bp
from routes.indirimlikurumlar import bp as indirim_bp
from routes.calculators import calculators_bp
from routes.mukellef_routes import bp as mukellef_bp
from routes.kdv_routes import bp as kdv_bp

try:
    from flask.json.provider import DefaultJSONProvider
except ImportError:
    from flask.json import JSONEncoder as DefaultJSONProvider

class SafeJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, Undefined):
            return None
        return super().default(obj)

app = Flask(__name__)
app.config.from_object("config")

# --- Configuration & Extensions ---
# Try to get DATABASE_URL, fallback to sqlite if missing to prevent total crash
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    print("WARNING: DATABASE_URL not found in environment. Falling back to SQLite.")
    _db_url = "sqlite:///instance/hesaptanit.db"

app.config["DATABASE_URL"] = _db_url

app.json = SafeJSONProvider(app)
limiter.init_app(app)

app.permanent_session_lifetime = timedelta(minutes=30)
app.secret_key = config.SECRET_KEY

# Session Config
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_NAME'] = 'isfa_session'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

app.debug = os.getenv("FLASK_DEBUG", "0") == "1"
app.config['ENV'] = 'production'

if not app.debug:
    import logging
    from logging.handlers import TimedRotatingFileHandler
    try:
        if not os.path.exists('logs'):
            os.makedirs('logs', exist_ok=True)
        # TimedRotatingFileHandler ile Windows lock sorunu önlenir
        file_handler = TimedRotatingFileHandler(
            'logs/hesaptanit.log',
            when='midnight',
            backupCount=10,
            encoding='utf-8',
            delay=True
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('HesapTanit startup in production mode')
    except Exception as log_err:
        print(f"Logging setup failed: {log_err}")

    # Talisman and Security
    from flask_talisman import Talisman
    Talisman(app, content_security_policy=None)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

# --- Context Processors & Filters ---
@app.context_processor
def inject_login_status():
    return dict(is_logged_in=session.get("logged_in", False))

app.jinja_env.filters["safe_date"] = safe_date
app.jinja_env.filters["currency"] = currency_filter 
app.jinja_env.filters["tlformat"] = tlformat

# --- Admin Bootstrap ---
def bootstrap_admin_from_env():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password: return

    hashed_pw = generate_password_hash(password)
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT password FROM users WHERE username = %s", (username,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO users (username, password, is_approved, role, has_kdv_access) VALUES (%s, %s, 1, 'admin', 1)", (username, hashed_pw))
                print(f"Admin hesabı oluşturuldu: {username}")
            else:
                # Eger kullanıcı varsa bilgilerini guncelle
                c.execute("UPDATE users SET password = %s, role = 'admin', has_kdv_access = 1 WHERE username = %s", (hashed_pw, username))
                print(f"Admin hesabı güncellendi: {username}")
        conn.commit()

# --- Blueprints Registration ---
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(data_bp)
app.register_blueprint(report_bp)
app.register_blueprint(tools_bp)
app.register_blueprint(indirim_bp)

app.register_blueprint(calculators_bp) 
app.register_blueprint(mukellef_bp)
app.register_blueprint(kdv_bp)

# --- Initialization & Database Check ---
with app.app_context():
    try:
        # Tables & Migrations
        app.logger.info("Running migrations...")
        migrate_users_table()   
        migrate_login_logs_table()
        migrate_tesvik_columns()
        migrate_tesvik_kullanim_table()
        migrate_profit_data_table()
        migrate_kdv_mukellef_table()
        migrate_kdv_tables()
        migrate_kdv_documents_table() 
        migrate_kdv_notes_table()
        migrate_mukellef_table()
        
        # Superuser
        bootstrap_admin_from_env()
        
        # Quick Connection Test
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        
        app.logger.info("Startup sequence completed successfully.")
        print("Baslangic kontrolleri tamamlandi.")
    except Exception as e:
        error_msg = f"Startup / Database Check Failure: {e}"
        print(f"⚠️ {error_msg}")
        app.logger.error(error_msg)
        import traceback
        app.logger.error(traceback.format_exc())

if __name__ == "__main__":
    app.run(debug=True)
