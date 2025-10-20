from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, session, make_response,
    send_from_directory, flash, send_file, current_app
)


from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jinja2 import Undefined
from fpdf import FPDF
from cryptography.fernet import Fernet






# Veri İşleme ve Analiz
import sqlite3
import pandas as pd
import pdfplumber
import re
import json
import hashlib
import pdfkit
import unicodedata
import difflib
import os
import io
import base64
import tempfile
import calendar
import xlsxwriter
import math
import traceback


from collections import defaultdict
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from io import BytesIO
from difflib import get_close_matches

import config
from hesaplar import BILANCO_HESAPLARI
from gelir import GELIR_TABLOSU_HESAPLARI
from finansal_oranlar import hesapla_finansal_oranlar, analiz_olustur
from auth import login_required
from services.db import get_conn, migrate_tesvik_columns
from routes.indirimlikurumlar import bp as indirim_bp
from routes.blog import blog_bp, blog_posts
from config import tarifeler, asgari_ucretler







app = Flask(__name__, instance_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'))



import os
from werkzeug.security import generate_password_hash
from services.db import get_conn

def bootstrap_admin_from_env():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        print("⚠️ Ortam değişkenleri tanımlı değil, admin oluşturulmadı.")
        return

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO users (username, password, is_approved)
                VALUES (?, ?, 1)
            """, (username, generate_password_hash(password)))
            conn.commit()
            print(f"✅ Admin kullanıcısı oluşturuldu ve onaylandı: {username}")
        else:
            print("ℹ️ Admin zaten mevcut.")




# --- Veritabanı kontrolü ve güvenli başlatma ---
from init_db import base_dir, database_path

if os.path.exists(database_path):
    print(f"✅ Mevcut veritabanı bulundu: {database_path}")
else:
    print("🆕 Veritabanı yok, ilk kez oluşturuluyor...")
    import init_db  # tablo yapısını kurar

    
    
    
# --- Flask-Limiter: Giriş denemelerini kısıtla ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

app.permanent_session_lifetime = timedelta(minutes=30)  # 30 dk



app.config.from_object(config)

app.config['DATABASE'] = os.path.join(app.instance_path, 'database.db')

os.makedirs(app.instance_path, exist_ok=True)

app.secret_key = app.config["SECRET_KEY"]

fernet = Fernet(app.config["FERNET_KEY"])

app.debug = True


limiter.enabled = False


@app.context_processor
def inject_login_status():
    # session['logged_in'] True/False tuttuğumuz için
    return dict(is_logged_in=session.get('logged_in', False))




with app.app_context():
    migrate_tesvik_columns()

    from services.db import migrate_users_table
    migrate_users_table()

    # Admin bootstrap da context içinde çalışmalı
    try:
        bootstrap_admin_from_env()
    except Exception as e:
        print(f"⚠️ Admin oluşturulurken hata: {e}")


app.register_blueprint(indirim_bp)
app.register_blueprint(blog_bp, url_prefix='/blog')



ALLOWED_EXTENSIONS = app.config["ALLOWED_EXTENSIONS"]

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )



FAVORI_DOSYA = "favoriler.json"
NOT_DOSYA = "notlar.json"


NEGATIVE_BILANCO_CODES = set([
    '103', '119', '122', '124', '129', '137', '139', '158',
    '199', '222', '224', '229', '237', '239', '241', '243',
    '244', '246', '247', '249', '257', '268', '278', '298',
    '299', '302', '308', '322', '337', '371', '402', '408',
    '422', '437', '501', '503', '580', '591'
])

NEGATIVE_GELIR_CODES = set([
    '610', '611', '612', '620', '621', '622', '623', '630',
    '631', '632', '653', '654', '655', '656', '657', '658',
    '659', '660', '661', '680', '681', '689', '690'
])




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        
        username = request.form["username"]
        password = request.form["password"]
        
        if not username or not password:
            flash("Kullanıcı adı ve şifre boş olamaz.", "warning")
            return render_template("register.html")
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalı.", "warning")
            return render_template("register.html")
        
        hashed_password = generate_password_hash(password)

        try:
            with get_conn() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success") # Kategori eklendi
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Bu kullanıcı adı zaten var. Lütfen farklı bir kullanıcı adı seçin.", "danger") # Kategori eklendi
            return render_template("register.html")
        
    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 10 minutes")  # 10 dakikada en fazla 5 deneme
def login():
    # Eğer kullanıcı zaten giriş yapmışsa, ana sayfaya yönlendir
    if session.get("user_id"):
        return redirect(url_for('home'))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id, password, is_approved FROM users WHERE username = ?", (username,))
            result = c.fetchone()
        
        if result and check_password_hash(result["password"], password):
            # 🧩 Onay kontrolü ekledik
            if result["is_approved"] == 0:
                flash("Hesabınız henüz admin tarafından onaylanmadı.", "warning")
                return render_template("login.html")

            # 🔐 Giriş başarılı
            session["user_id"] = result["id"]
            session["user"] = username
            session['logged_in'] = True 
            session.permanent = True  # 30 dk session süresi aktif
            
            flash(f"Hoş geldiniz, {username}!", "success") 

            # 👑 Admin ise doğrudan admin paneline yönlendir
            if username.lower() == "admin":
                return redirect(url_for("admin_users"))
            else:
                return redirect(url_for("home")) 
        else:
            flash("Hatalı kullanıcı adı veya şifre.", "danger") 
            return render_template("login.html")
    
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()  # Tüm session bilgilerini temizle
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for("home"))



@app.route("/")
def home():
    latest_posts = sorted(blog_posts, key=lambda x: x['publish_date'], reverse=True)[:3]
    is_logged_in = session.get('logged_in', False)

    stats = {
        "experience_years": 15,        # 15+ yıl tecrübe
        "financial_ratios": 23,        # sistemde tanımlı oran sayısı
        "ymm_cities": 2,               # iki farklı ilde iki ofis
    }

    return render_template(
        "index.html",
        latest_posts=latest_posts,
        is_logged_in=is_logged_in,
        stats=stats
    )



# --- Kullanıcı Yönetimi: Admin paneli ---
@app.route("/admin/users")
@login_required
def admin_users():
    # Sadece admin kullanıcı görebilsin
    if session.get("user") != "admin":
        flash("Bu sayfaya erişim izniniz yok.", "danger")
        return redirect(url_for("home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, username, is_approved FROM users")
        users = c.fetchall()
    return render_template("admin_users.html", users=users)


@app.route("/admin/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    if session.get("user") != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
        conn.commit()
    flash("Kullanıcı başarıyla onaylandı ✅", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/reject/<int:user_id>")
@login_required
def reject_user(user_id):
    if session.get("user") != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("home"))

    with get_conn() as conn:
        c = conn.cursor()

        # Kullanıcı adı admin olan hesap silinemez
        c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        if row and row["username"].lower() == "admin":
            flash("Admin hesabı silinemez ❌", "warning")
            return redirect(url_for("admin_users"))

        # Diğer kullanıcıyı sil
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

    flash("Kullanıcı kaydı silindi ❌", "info")
    return redirect(url_for("admin_users"))



from werkzeug.security import generate_password_hash, check_password_hash
import re

# --- Kullanıcı kendi şifresini değiştirme ---
@limiter.limit("5 per 5 minutes")
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    # Kullanıcının oturumda olduğundan emin ol (login_required ile garanti)
    username = session.get("user")
    if not username:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        current = request.form.get("current_password", "")
        new1 = request.form.get("new_password", "")
        new2 = request.form.get("new_password_confirm", "")

        # Basit doğrulamalar
        if not current or not new1 or not new2:
            flash("Tüm alanları doldurun.", "warning")
            return render_template("change_password.html")

        if new1 != new2:
            flash("Yeni şifreler eşleşmiyor.", "warning")
            return render_template("change_password.html")

        # Parola güçlülüğü (örnek): en az 8 karakter ve rakam içermeli
        if len(new1) < 8 or not re.search(r"\d", new1) or not re.search(r"[A-Za-z]", new1):
            flash("Yeni şifre en az 8 karakter olmalı ve hem harf hem rakam içermelidir.", "warning")
            return render_template("change_password.html")

        # Mevcut parola kontrolü
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            row = c.fetchone()

            if not row or not check_password_hash(row["password"], current):
                flash("Mevcut şifre hatalı.", "danger")
                return render_template("change_password.html")

            # Güncelle
            new_hash = generate_password_hash(new1)
            c.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, row["id"]))
            conn.commit()

        flash("Şifreniz başarıyla değiştirildi.", "success")
        return redirect(url_for("home"))

    return render_template("change_password.html")



# --- Admin: herhangi bir kullanıcının şifresini sıfırlama ---
@app.route("/admin/reset_password/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin_reset_password(user_id):
    if session.get("user") != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            flash("Kullanıcı bulunamadı.", "warning")
            return redirect(url_for("admin_users"))

    if request.method == "POST":
        new1 = request.form.get("new_password", "")
        new2 = request.form.get("new_password_confirm", "")

        if not new1 or not new2:
            flash("Lütfen yeni şifre alanlarını doldurun.", "warning")
            return render_template("admin_reset_password.html", user=user)

        if new1 != new2:
            flash("Yeni şifreler eşleşmiyor.", "warning")
            return render_template("admin_reset_password.html", user=user)

        # Parola güçlülüğü kontrolü
        if len(new1) < 8 or not re.search(r"\d", new1) or not re.search(r"[A-Za-z]", new1):
            flash("Yeni şifre en az 8 karakter olmalı ve hem harf hem rakam içermelidir.", "warning")
            return render_template("admin_reset_password.html", user=user)

        # Admin kendi hesabını sıfırlıyorsa ekstra onay (opsiyonel)
        if user["username"].lower() == "admin" and session.get("user") != "admin":
            flash("Admin hesabını sadece admin değiştirebilir.", "danger")
            return redirect(url_for("admin_users"))

        new_hash = generate_password_hash(new1)
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()

        flash(f"{user['username']} kullanıcısının şifresi sıfırlandı.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_reset_password.html", user=user)





@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')




@app.template_filter('tlformat')
def tlformat(value):
    if value is None or isinstance(value, Undefined):
        return "-"
    try:
        return '{:,.2f}'.format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError): # Hata yakalama genişletildi
        return str(value)
    
@app.template_filter('currency')
def currency_filter(amount):
    try:
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return amount or "-"




@app.route('/sitemap.xml')
def sitemap():
    pages = []
    now = datetime.now().date().isoformat()

    static_urls = [
        # Ana sayfa ve bölümler
        ('home', {}),  # https://www.isfaymm.com/
        # Alt bölümler (tek sayfa içinde anchor linkler)
        ('home', {'_anchor': 'services'}),   # https://www.isfaymm.com/#services
        ('home', {'_anchor': 'about'}),      # https://www.isfaymm.com/#about
        ('home', {'_anchor': 'team'}),       # https://www.isfaymm.com/#team
        ('home', {'_anchor': 'blog'}),       # https://www.isfaymm.com/#blog
        ('home', {'_anchor': 'contact'}),    # https://www.isfaymm.com/#contact

        # Bağımsız sayfalar
        ('contact', {}),                     # https://www.isfaymm.com/contact
        ('indirimlikurumlar.index', {}),     # https://www.isfaymm.com/indirimlikurumlar
        ('asgari', {}),                      # https://www.isfaymm.com/asgari
        ('sermaye', {}),                     # https://www.isfaymm.com/sermaye
        ('finansman', {}),                   # https://www.isfaymm.com/finansman

        # Blog (liste sayfası)
        ('blog.index', {}),                  # https://www.isfaymm.com/blog
    ]

    # URL’leri oluştur
    for endpoint, params in static_urls:
        try:
            url = f"https://www.isfaymm.com{url_for(endpoint, **params)}"
            pages.append(url)
        except Exception as e:
            print(f"Sitemap URL hatası ({endpoint}):", e)

    # XML çıktı oluştur
    xml = render_template('sitemap_template.xml', pages=pages, lastmod=now)
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response




def to_float_turkish(s):
    """
    Türk Lirası formatındaki sayısal stringi (örneğin '1.234,56', '(1.234,56)', '1.234,56 -') float'a dönüştürür.
    """

    if isinstance(s, (int, float)):
        return s

    if s is None or pd.isna(s) or str(s).strip() == '':
        return None
    
    original_s = s
    s = str(s).strip() 


    is_negative_parentheses = False
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1] 
        is_negative_parentheses = True
    
    
    is_negative_trailing_dash = False
    if s.endswith('-'):
        s = s[:-1].strip() 
        is_negative_trailing_dash = True

  
    s = s.replace('.', '').replace(',', '.')
    
    try:
        float_val = float(s)
        if is_negative_parentheses or is_negative_trailing_dash:
            float_val = -float_val # Negatif işareti uygula
        # print(f"DEBUG(to_float_turkish): Orijinal: '{original_s}', İşlenmiş: '{s}', Sonuç: {float_val}") # Debug için
        return float_val
    except ValueError as e:
        # print(f"ERROR(to_float_turkish): '{original_s}' float'a dönüştürülemedi. Hata: {e}") # Debug için
        return None



def extract_mukellef_bilgileri(text: str):
    import re
    
    unvan = "Bilinmiyor"
    donem = "Bilinmiyor"
    vkn   = "Bilinmiyor"
    tur   = "Bilinmiyor"

    # --- Unvan ---
    match1 = re.search(r"Soyadı \(Unvanı\)\s+([^\n]+)", text)
    match2 = re.search(r"Adı \(Unvanın Devamı\)\s+([^\n]+)", text)
    if match1 and match2:
        unvan = f"{match1.group(1).strip()} {match2.group(1).strip()}".upper()
    elif match1:
        unvan = match1.group(1).strip().upper()

    # --- VKN ---
    m_vkn = re.search(r"Vergi Kimlik (?:No|Numarası)(?:\s*\(TC Kimlik No\))?\s+(\d{10,11})", text)
    if m_vkn:
        vkn = m_vkn.group(1).strip()

    # --- Tür ---
    if "KURUMLAR VERGİSİ BEYANNAMESİ" in text.upper():
        tur = "Kurumlar"
        if "Bilanço" in text or "Kazancın Tespit Yöntemi Bilanço" in text:
            tur = "Bilanço"
        elif "GELİR TABLOSU" in text:
            tur = "Gelir Tablosu"
    elif "KATMA DEĞER VERGİSİ BEYANNAMESİ" in text.upper():
        tur = "KDV"

    # --- Dönem ---
    if tur == "KDV":
        # KDV'de Ay + Yıl varsa → "Ocak / 2025"
        m1 = re.search(r"Yıl\s+(\d{4}).*?Ay\s+([A-Za-zÇÖŞİÜĞçöşıüğ]+)", text, re.IGNORECASE | re.DOTALL)
        m2 = re.search(r"Ay\s+([A-Za-zÇÖŞİÜĞçöşıüğ]+).*?Yıl\s+(\d{4})", text, re.IGNORECASE | re.DOTALL)
        if m1:
            donem = f"{m1.group(2).capitalize()} / {m1.group(1)}"
        elif m2:
            donem = f"{m2.group(1).capitalize()} / {m2.group(2)}"
    else:
        # Kurumlar'da sadece yıl
        m3 = re.search(r"DÖNEM TİPİ.*?Yıl\s+(\d{4})", text, re.IGNORECASE | re.DOTALL)
        if m3:
            donem = m3.group(1)
        else:
            m4 = re.search(r"DÖNEM[:\s]+(\d{4})", text)
            if m4:
                donem = m4.group(1)

    print(f"[DEBUG] Unvan={unvan}, Donem={donem}, VKN={vkn}, Tür={tur}")
    return {
        "unvan": unvan,
        "donem": donem,
        "vergi_kimlik_no": vkn,
        "tur": tur
    }



@app.route("/veri-giris", methods=["GET"]) 
@login_required
def veri_giris():
    secili_vkn   = request.args.get("vkn")    # ✅ artık VKN parametresi alıyoruz
    secili_donem = request.args.get("donem")

    mukellefler = []
    donemler = []
    yuklenen_tum_belgeler = []

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()


        uid = session.get("user_id")
        c.execute(
            "SELECT vergi_kimlik_no, unvan FROM mukellef WHERE user_id=? ORDER BY unvan",
            (uid,)
        )
        mukellefler = [{"vergi_kimlik_no": row["vergi_kimlik_no"], "unvan": row["unvan"]} for row in c.fetchall()]

        if secili_vkn:
            # ✅ Seçilen mükellefe ait dönemleri getir
            c.execute("""
                SELECT DISTINCT b.donem 
                FROM beyanname b
                JOIN mukellef m ON b.mukellef_id = m.id
                WHERE m.vergi_kimlik_no = ? AND m.user_id = ?
                ORDER BY b.donem DESC
            """, (secili_vkn, uid))
            donemler = [row["donem"] for row in c.fetchall()]

            # ✅ Seçili VKN ve döneme ait tüm beyannameleri getir
            if secili_donem:
                c.execute("""
                    SELECT b.id, m.unvan, m.vergi_kimlik_no, b.donem, b.tur, 
                        b.veriler, b.yuklenme_tarihi
                    FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id = m.id
                    WHERE m.vergi_kimlik_no = ? AND m.user_id = ? AND b.donem = ?
                    ORDER BY b.yuklenme_tarihi DESC
                """, (secili_vkn, uid, secili_donem))
            else:
                c.execute("""
                    SELECT b.id, m.unvan, m.vergi_kimlik_no, b.donem, b.tur, 
                        b.veriler, b.yuklenme_tarihi
                    FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id = m.id
                    WHERE m.vergi_kimlik_no = ? AND m.user_id = ?
                    ORDER BY b.donem DESC, b.yuklenme_tarihi DESC
                """, (secili_vkn, uid))


            rows = c.fetchall()
            for r in rows:
                # ✅ Tarihi dönüştür
                tarih = r["yuklenme_tarihi"]
                if tarih:
                    try:
                        utc_dt = datetime.strptime(tarih, "%Y-%m-%d %H:%M:%S")
                        istanbul_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Istanbul"))
                        tarih = istanbul_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        print(f"Hata: Belge yükleme tarihi dönüşümünde problem: {e}")
                        tarih = "Tarih Hatası"
                else:
                    tarih = "Tarih Yok"


                yuklenen_tum_belgeler.append({
                    "id": r["id"],
                    "unvan": r["unvan"],
                    "vkn": r["vergi_kimlik_no"],   # ✅ artık VKN’yi de UI’ye taşı
                    "donem": r["donem"],
                    "belge_turu": r["tur"],       # belge_turu yerine tur
                    "yuklenme_tarihi": tarih
                    
                })

    # ✅ Mizan kontrolü
    has_mizan_for_selected_period = any(
        belge["belge_turu"] == "mizan" and
        belge["vkn"] == secili_vkn and
        belge["donem"] == secili_donem
        for belge in yuklenen_tum_belgeler
    )

    return render_template(
        "veri_giris.html",
        mukellefler=mukellefler,
        donemler=donemler,
        secili_vkn=secili_vkn,
        secili_donem=secili_donem,
        yuklenen_tum_belgeler=yuklenen_tum_belgeler,
        has_mizan_for_selected_period=has_mizan_for_selected_period
    )



from io import BytesIO
from PyPDF2 import PdfReader

@app.route("/yukle-coklu", methods=["POST"])
@login_required
def yukle_coklu():
    uploaded_files = request.files.getlist("belgeler")
    mesajlar = []

    for file in uploaded_files:
        filename = secure_filename(file.filename)
        if filename == "":
            mesajlar.append({
                "type": "warning",
                "title": "Uyarı",
                "text": "Boş dosya adı atlandı."
            })
            continue

        file_extension = filename.rsplit(".", 1)[1].lower()
        if not allowed_file(file.filename):
            mesajlar.append({
                "type": "error",
                "title": "❌ Geçersiz Dosya",
                "text": f"'{file.filename}' geçersiz. Sadece PDF, XLSX, XLS kabul edilir."
            })
            continue

        try:
            # ✅ Belleğe al
            file_bytes = file.read()
            buffer = BytesIO(file_bytes)

            if file_extension == "pdf":
                try:
                    reader = PdfReader(buffer)
                    text = "".join(page.extract_text() or "" for page in reader.pages)
                    text_upper = text.upper()

                    if "KATMA DEĞER VERGİSİ BEYANNAMESİ" in text_upper:
                        sonuc = parse_kdv_from_pdf(BytesIO(file_bytes))
                        if sonuc and sonuc.get("vergi_kimlik_no") != "Bilinmiyor":
                            mesajlar += kaydet_beyanname(sonuc, "kdv")

                    elif "KURUMLAR VERGİSİ BEYANNAMESİ" in text_upper:
                        sonuc_bilanco = parse_bilanco_from_pdf(BytesIO(file_bytes))
                        if sonuc_bilanco and sonuc_bilanco.get("vergi_kimlik_no") != "Bilinmiyor":
                            mesajlar += kaydet_beyanname(sonuc_bilanco, "bilanco")

                        sonuc_gelir = parse_gelir_from_pdf(BytesIO(file_bytes))
                        if sonuc_gelir and sonuc_gelir.get("vergi_kimlik_no") != "Bilinmiyor":
                            mesajlar += kaydet_beyanname(sonuc_gelir, "gelir")

                    else:
                        mesajlar.append({
                            "type": "warning",
                            "title": "❓ Tanınmayan PDF",
                            "text": f"'{filename}' hangi tür olduğu anlaşılamadı."
                        })

                except Exception as e:
                    mesajlar.append({
                        "type": "error",
                        "title": "❌ PDF Hatası",
                        "text": f"'{filename}' okunamadı: {e}"
                    })

            elif file_extension in ["xlsx", "xls"]:
                mesajlar.append({
                    "type": "mizan_input_required",
                    "filename": filename,
                    "title": "Mizan Bilgileri Gerekli",
                    "text": f"'{filename}' mizan dosyası için mükellef ve dönem bilgilerini giriniz."
                })

        except Exception as e:
            import traceback
            print("=== YÜKLE HATASI ===")
            print(traceback.format_exc())   # ✅ Burada detaylı log göreceksin
            mesajlar.append({
                "type": "error",
                "title": "Yükleme Hatası",
                "text": f"'{filename}' yüklenemedi: {e}"
            })

    return jsonify(mesajlar)




def kaydet_beyanname(sonuc, belge_turu):
    mesajlar = []
    file_vkn   = sonuc.get("vergi_kimlik_no", "")
    file_unvan = sonuc.get("unvan", "")
    file_donem = sonuc.get("donem", "")
    veriler    = sonuc.get("veriler", {})

    if not file_vkn or file_vkn == "Bilinmiyor" or not file_donem or file_donem == "Bilinmiyor":
        mesajlar.append({
            "type": "error",
            "title": "❌ Tanınmadı",
            "text": "Dosyadan VKN/Dönem okunamadı, yüklenmedi."
        })
        return mesajlar

    # --- JSON yapısını normalize et (şablon uyum garantisi) ---
    if belge_turu == "bilanco":
        veriler = { 
            "aktif": veriler.get("aktif", []),
            "pasif": veriler.get("pasif", []),
            "toplamlar": veriler.get("toplamlar") 
                or veriler.get("direct_totals") 
                or {"AKTİF": {}, "PASİF": {}},
            "aktif_alt_toplamlar": veriler.get("aktif_alt_toplamlar", {}),
            "pasif_alt_toplamlar": veriler.get("pasif_alt_toplamlar", {}),
            "has_inflation": veriler.get("has_inflation", False)
        }

    elif belge_turu == "gelir":
        veriler = [
            {
                "kod": row.get("kod"),
                "aciklama": row.get("aciklama"),
                "onceki_donem": row.get("onceki_donem"),
                "cari_donem": row.get("cari_donem")
            }
            for row in veriler
        ]

    elif belge_turu == "kdv":
        veriler = {
            "donem": file_donem,
            "unvan": file_unvan,
            "vergi_kimlik_no": file_vkn,
            "veriler": veriler if isinstance(veriler, list) else []
        }
        
    uid = session.get("user_id")
    if not uid:
        return [{
            "type": "error",
            "title": "❌ Oturum Hatası",
            "text": "Kullanıcı oturumu bulunamadı."
        }]

    with get_conn() as conn:
        c = conn.cursor()

        # --- mükellef kontrol ---
        c.execute("SELECT id FROM mukellef WHERE user_id=? AND vergi_kimlik_no=?", (uid, file_vkn))
        row = c.fetchone()
        if row:
            mukellef_id = row[0]
            c.execute("UPDATE mukellef SET unvan=? WHERE id=? AND user_id=?", (file_unvan, mukellef_id, uid))
        else:
            c.execute(
                "INSERT INTO mukellef (user_id, vergi_kimlik_no, unvan) VALUES (?, ?, ?)",
                (uid, file_vkn, file_unvan)
            )
            mukellef_id = c.lastrowid

        # --- veriyi şifrele ---
        encrypted_data = fernet.encrypt(
            json.dumps(veriler, ensure_ascii=False).encode("utf-8")
        )

        # --- beyanname kontrol ---
        c.execute("""
            SELECT id FROM beyanname 
            WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?
        """, (uid, mukellef_id, file_donem, belge_turu))
        existing = c.fetchone()

        if existing:
            # ✅ Güncelleme
            c.execute("""
                UPDATE beyanname 
                SET veriler=?, yuklenme_tarihi=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (encrypted_data, existing[0]))
            mesajlar.append({
                "type": "info",
                "title": "🔄 Güncellendi",
                "text": f"{file_unvan} / {file_donem} - {belge_turu.upper()} güncellendi."
            })
        else:
            # ✅ Yeni kayıt
            c.execute("""
                INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler) 
                VALUES (?, ?, ?, ?, ?)
            """, (uid, mukellef_id, file_donem, belge_turu, encrypted_data))
            mesajlar.append({
                "type": "success",
                "title": "✅ Yüklendi",
                "text": f"{file_unvan} / {file_donem} - {belge_turu.upper()} başarıyla yüklendi."
            })

        conn.commit()
        
        # 🔄 Ek olarak, eğer bilanço dosyasında "önceki dönem" verisi varsa, onu da DB'ye yaz
        if belge_turu == "bilanco":
            try:
                aktif_df = pd.DataFrame(veriler.get("aktif", []))
                pasif_df = pd.DataFrame(veriler.get("pasif", []))

                if (
                    "Önceki Dönem" in aktif_df.columns and aktif_df["Önceki Dönem"].sum() != 0
                ) or (
                    "Önceki Dönem" in pasif_df.columns and pasif_df["Önceki Dönem"].sum() != 0
                ):
                    onceki_yil = str(int(file_donem) - 1)

                    aktif_prev = aktif_df[["Kod", "Açıklama", "Önceki Dönem"]].rename(columns={"Önceki Dönem": "Cari Dönem"})
                    pasif_prev = pasif_df[["Kod", "Açıklama", "Önceki Dönem"]].rename(columns={"Önceki Dönem": "Cari Dönem"})

                    veriler_prev = {
                        "aktif": aktif_prev.to_dict(orient="records"),
                        "pasif": pasif_prev.to_dict(orient="records"),
                        "toplamlar": veriler.get("toplamlar", {"AKTİF": {}, "PASİF": {}}),
                        "has_inflation": veriler.get("has_inflation", False)
                    }

                    encrypted_prev = fernet.encrypt(
                        json.dumps(veriler_prev, ensure_ascii=False).encode("utf-8")
                    )

                    c.execute("""
                        SELECT id FROM beyanname
                        WHERE user_id=? AND mukellef_id=? AND donem=? AND tur='bilanco'
                    """, (uid, mukellef_id, onceki_yil))
                    exists_prev = c.fetchone()

                    if exists_prev:
                        c.execute("""
                            UPDATE beyanname
                            SET veriler=?, yuklenme_tarihi=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (encrypted_prev, exists_prev[0]))
                        mesajlar.append({
                            "type": "info",
                            "title": "🔁 Önceki Dönem Güncellendi",
                            "text": f"{file_unvan} / {onceki_yil} - BİLANÇO güncellendi (otomatik)."
                        })
                    else:
                        c.execute("""
                            INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler)
                            VALUES (?, ?, ?, 'bilanco', ?)
                        """, (uid, mukellef_id, onceki_yil, encrypted_prev))
                        mesajlar.append({
                            "type": "success",
                            "title": "➕ Önceki Dönem Eklendi",
                            "text": f"{file_unvan} / {onceki_yil} - BİLANÇO otomatik oluşturuldu."
                        })

                    conn.commit()
                    current_app.logger.info(f"[AUTO-SAVE] {file_donem} PDF'inden {onceki_yil} bilanço üretildi.")

            except Exception as e:
                current_app.logger.warning(f"[AUTO-SAVE] Önceki dönem kaydedilemedi: {e}")
        
        # 🔄 Ek olarak, eğer gelir tablosu dosyasında "önceki dönem" verisi varsa, onu da DB'ye yaz
        elif belge_turu == "gelir":
            try:
                # Veriler list formatında mı kontrol et
                tablo = veriler if isinstance(veriler, list) else veriler.get("tablo") or veriler.get("veriler") or []
                df_gelir = pd.DataFrame(tablo)

                # Eğer önceki dönem sütunu yoksa veya değerler sıfırsa, geç
                if "onceki_donem" in df_gelir.columns and df_gelir["onceki_donem"].fillna(0).sum() != 0:
                    onceki_yil = str(int(file_donem) - 1)

                    # Sadece önceki dönem sütununu "cari_donem" olarak yeniden adlandır
                    df_prev = df_gelir.copy()
                    df_prev["cari_donem"] = df_prev["onceki_donem"]
                    df_prev["onceki_donem"] = None

                    veriler_prev = [
                        {
                            "kod": row.get("kod"),
                            "aciklama": row.get("aciklama"),
                            "onceki_donem": None,
                            "cari_donem": row.get("cari_donem")
                        }
                        for _, row in df_prev.iterrows()
                    ]

                    encrypted_prev = fernet.encrypt(
                        json.dumps(veriler_prev, ensure_ascii=False).encode("utf-8")
                    )

                    c.execute("""
                        SELECT id FROM beyanname
                        WHERE user_id=? AND mukellef_id=? AND donem=? AND tur='gelir'
                    """, (uid, mukellef_id, onceki_yil))
                    exists_prev = c.fetchone()

                    if exists_prev:
                        c.execute("""
                            UPDATE beyanname
                            SET veriler=?, yuklenme_tarihi=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (encrypted_prev, exists_prev[0]))
                        mesajlar.append({
                            "type": "info",
                            "title": "🔁 Önceki Dönem Güncellendi",
                            "text": f"{file_unvan} / {onceki_yil} - GELİR TABLOSU güncellendi (otomatik)."
                        })
                    else:
                        c.execute("""
                            INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler)
                            VALUES (?, ?, ?, 'gelir', ?)
                        """, (uid, mukellef_id, onceki_yil, encrypted_prev))
                        mesajlar.append({
                            "type": "success",
                            "title": "➕ Önceki Dönem Eklendi",
                            "text": f"{file_unvan} / {onceki_yil} - GELİR TABLOSU otomatik oluşturuldu."
                        })

                    conn.commit()
                    current_app.logger.info(f"[AUTO-SAVE][GELİR] {file_donem} PDF'inden {onceki_yil} gelir tablosu üretildi.")

            except Exception as e:
                current_app.logger.warning(f"[AUTO-SAVE][GELİR] Önceki dönem kaydedilemedi: {e}")

    return mesajlar


@app.route("/pdf-belgeler-tablo/<string:tur>", methods=["GET"])
@login_required
def pdf_belgeler_tablo(tur):
    vkn   = request.args.get("vkn")
    unvan = request.args.get("unvan")
    donem = request.args.get("donem")
    secilen_donem_turu = request.args.get("donem_turu", "cari")
    
    if secilen_donem_turu not in ("onceki", "cari", "cari_enflasyon"):
        secilen_donem_turu = "cari"

    if not (tur and vkn and donem):
        flash("❗ Eksik parametre.")
        return redirect(url_for("veri_giris"))
    
    uid = session["user_id"]

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, unvan FROM mukellef WHERE user_id=? AND vergi_kimlik_no=?", (uid, vkn))
        row = c.fetchone()
        if not row:
            flash("❗ Mükellef bulunamadı.")
            return redirect(url_for("veri_giris"))
        

        
        mid = row["id"]
        unvan = row["unvan"]

        c.execute("SELECT veriler FROM beyanname WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?",
                  (uid, mid, donem, tur.lower()))
        row = c.fetchone()

    if not row:
        flash("❗ Belge bulunamadı.")
        return redirect(url_for("veri_giris", unvan=unvan, donem=donem))
    
    # 🔓 Decrypt et
    decrypted_data = fernet.decrypt(row["veriler"]).decode("utf-8")
    veriler = json.loads(decrypted_data)



    # --- Bilanço ---
    if tur == "bilanco":
        aktif_list = veriler.get("aktif", [])
        pasif_list = veriler.get("pasif", [])
        toplamlar = veriler.get("toplamlar", {"AKTİF": {}, "PASİF": {}})
        aktif_alt_toplamlar = veriler.get("aktif_alt_toplamlar", {})
        pasif_alt_toplamlar = veriler.get("pasif_alt_toplamlar", {})
        
        has_inflation = veriler.get("has_inflation", False)

        donem_mapping = {
            "onceki": str(int(donem) - 1) if donem.isdigit() else "Önceki",
            "cari": donem
        }
        if has_inflation:
            donem_mapping["cari_enflasyon"] = donem

        return render_template(
            "tablo_bilanco.html",
            vkn=vkn,
            unvan=unvan,
            donem=donem,
            aktif_list=aktif_list,
            pasif_list=pasif_list,
            toplamlar=toplamlar,
            secilen_donem=secilen_donem_turu,
            donem_mapping=donem_mapping,
            has_inflation=has_inflation,
            aktif_alt_toplamlar=aktif_alt_toplamlar,
            pasif_alt_toplamlar=pasif_alt_toplamlar
        )

    elif tur == "kdv":
        kdv_dict = veriler

        kdv_data = {}
        kdv_months = []

        # DB'de tek dönem saklı olduğu için secili_donemler tek elemanlı olacak
        raw_donem = kdv_dict.get("donem", donem)
        if raw_donem:
            kdv_months.append(raw_donem)

        for rec in kdv_dict.get("veriler", []):
            alan, deger = rec.get("alan"), rec.get("deger")
            if alan:
                kdv_data.setdefault(alan, {})[raw_donem] = deger

        return render_template(
            "rapor_kdv.html",
            secili_unvan=kdv_dict.get("unvan", unvan),
            secili_vkn=kdv_dict.get("vergi_kimlik_no", vkn),
            secili_donemler=[raw_donem],
            kdv_data=kdv_data,
            kdv_months=kdv_months
        )
        
    elif tur == "gelir":
        try:
            # --- Veri yapısını normalize et ---
            if isinstance(veriler, list):
                tablo = veriler
            elif isinstance(veriler, dict):
                tablo = veriler.get("tablo") or veriler.get("veriler") or []
            else:
                tablo = []
        except Exception as e:
            current_app.logger.error(f"[GELİR] Veri çözme hatası: {e}")
            tablo = []

        # --- Listeyi dict'e çevir ---
        tablo = [dict(r) for r in tablo if isinstance(r, (dict, sqlite3.Row))]

        current_app.logger.info(
            f"[GELİR] tablo satır sayısı: {len(tablo)} | veri_tipi={type(veriler)} | secilen_donem={secilen_donem_turu}"
        )

        # --- İlk birkaç satırı logla ---
        for i, r in enumerate(tablo[:10]):
            kod = r.get("kod")
            aciklama = r.get("aciklama")
            onceki = r.get("onceki_donem")
            cari = r.get("cari_donem")
            current_app.logger.info(
                f"[DEBUG][GELİR] Satır {i} -> kod={kod} | açıklama={aciklama} | önceki={onceki} | cari={cari}"
            )

        # --- Eğer veri yoksa uyar ve geri dön ---
        if not tablo:
            flash("❗ Seçilen döneme ait gelir tablosu verisi bulunamadı.")
            return redirect(url_for("veri_giris", vkn=vkn, donem=donem))

        # --- Dönem eşlemesi ---
        donem_mapping = {
            "onceki": str(int(donem) - 1) if donem.isdigit() else "Önceki",
            "cari": donem
        }

        # ✅ Gösterilecek kolon adını belirle
        if secilen_donem_turu == "onceki":
            gorunen_kolon = "onceki_donem"
        else:
            gorunen_kolon = "cari_donem"

        current_app.logger.info(
            f"[GELİR][RENDER] unvan={unvan} | donem={donem} | secilen_donem_turu={secilen_donem_turu} | gorunen_kolon={gorunen_kolon}"
        )

        try:
            return render_template(
                "tablo_gelir.html",
                tablo=tablo,
                unvan=unvan,
                donem=donem,
                vkn=vkn,
                donem_mapping=donem_mapping,
                secilen_donem=secilen_donem_turu,
                gorunen_kolon=gorunen_kolon  # 👈 bu kritik!
            )
        except Exception as e:
            # 🔥 render sırasında hata olursa logla
            current_app.logger.error(f"[GELİR][RENDER ERROR]: {e}", exc_info=True)
            flash("❗ Gelir tablosu görüntülenirken hata oluştu.")
            return redirect(url_for("veri_giris", vkn=vkn, donem=donem))



    flash("❗ Geçersiz tablo türü.")
    return redirect(url_for("veri_giris", unvan=unvan, donem=donem))




num_val_pattern_str = r"[-+]?(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d{2})?(?:\s*\([^\)]*\)|\s*-\s*)?"
find_all_nums_in_line = re.compile(num_val_pattern_str)



def find_account_code(block_name, description, parent_group=None):

    original_description = description.strip()


    kod_match = re.match(r"^\s*(\d{1,3})\s*[.\-]?\s*(.*)", original_description)

    if kod_match:
        kod = kod_match.group(1)
        if parent_group:
            print(f"[DEBUG] {block_name} -> {original_description} | kod={kod} (direct)")
        return kod

    # Sadece başlık satırıysa (örneğin "A. Hazır Değerler"), kod boş
    if re.match(r"^\s*([A-ZÇĞİÖŞÜ]|[IVXLCDM]+)\.\s*[\w\s\-()]+$", original_description):
        return ""

    # Açıklamayı temizle (noktalama ve büyük harf farklarını kaldır)
    description_clean = re.sub(r"^\s*[\.\s]+", "", original_description)
    description_clean = re.sub(r"[^\w\s]", "", description_clean.lower().strip())

    best_match = ""
    best_score = 0

    # İlgili ana bloğu al (AKTİF veya PASİF)
    ana_blok = BILANCO_HESAPLARI.get(block_name.upper(), {})

    for grup, alt_gruplar in ana_blok.items():
        # Eğer parent_group belirtildiyse ve bu grup değilse atla
        if parent_group and parent_group.strip().lower() != grup.strip().lower():
            continue

        for alt_grup, kod_dict in alt_gruplar.items():
            for kod, tanim in kod_dict.items():
                tanim_clean = tanim.lower().strip()
                tanim_clean_simple = re.sub(r"^\d+\.\s*", "", tanim_clean)
                tanim_clean_simple = re.sub(r"[^\w\s]", "", tanim_clean_simple)

                # Tam eşleşme varsa hemen döndür
                if description_clean == tanim_clean_simple or description_clean in tanim_clean_simple:
                    return kod

                # Çok uzun fark varsa fuzzy arama yapma
                if abs(len(tanim_clean_simple) - len(description_clean)) > 30:
                    continue

                score = difflib.SequenceMatcher(None, description_clean, tanim_clean_simple).ratio()
                if score > best_score and score > 0.65:
                    best_match = kod
                    best_score = score

    return best_match



def parse_numeric_columns(line_stripped):
    """
    Satırdan açıklamayı ve sayısal değerleri ayıklar.
    1, 2 veya 3 sütunlu (Önceki / Cari / Enflasyonlu) destekler.
    """
    # Satırdaki tüm sayıları bul
    numeric_values = re.findall(r"\d[\d\.\,]*", line_stripped)
    numeric_values = [v for v in numeric_values if v.strip()]

    onceki = cari = cari_enflasyon = None
    if len(numeric_values) >= 3:
        onceki = to_float_turkish(numeric_values[-3])
        cari = to_float_turkish(numeric_values[-2])
        cari_enflasyon = to_float_turkish(numeric_values[-1])
    elif len(numeric_values) == 2:
        onceki = to_float_turkish(numeric_values[0])
        cari = to_float_turkish(numeric_values[1])
    elif len(numeric_values) == 1:
        cari = to_float_turkish(numeric_values[0])

    # Açıklamadan tüm sayı gruplarını temizle
    desc_clean = re.sub(r"\d[\d\.\,]*", "", line_stripped)
    desc_clean = re.sub(r"\s{2,}", " ", desc_clean)  # fazla boşlukları düzelt
    desc_clean = re.sub(r"[\.]+(?=\s|$)", ".", desc_clean)  # nokta-temizleme
    description = desc_clean.strip(" .-•").strip()

    return description, onceki, cari, cari_enflasyon



def parse_table_block(text: str, block_name: str = "AKTİF", debug: bool = True):
    """
    PDF metninden belirtilen bilanço bloğunu (AKTİF veya PASİF) tablo olarak çıkarır.
    Debug True olduğunda satır satır log basar.
    """
    # Tablo başlangıcı
    header_pattern = (
        rf"{block_name}[\s\S]*?Açıklama.*?(?:\n.*?Cari Dönem)?[\s\S]*?\(\d{{4}}\).*?\(\d{{4}}\)"
    )
    end_pattern = rf"(?i)\n\s*{block_name}\s*TOPLAMI"

    block_start_match = re.search(header_pattern, text, re.DOTALL | re.IGNORECASE)
    if not block_start_match:
        if debug:
            sample = "\n".join(text.splitlines()[:40])
            print(f"[DEBUG] {block_name}: header bulunamadı.\n--- İlk 40 satır ---\n{sample}")
        return pd.DataFrame(columns=["Kod", "Açıklama", "Önceki Dönem", "Cari Dönem"]), False

    header_line_text_full_match = block_start_match.group(0)
    has_inflation_column_from_header = bool(
        re.search(r"enflasyon", header_line_text_full_match, re.IGNORECASE)
    )

    content_after_start = text[block_start_match.end():]
    block_end_match = re.search(end_pattern, content_after_start, re.DOTALL | re.IGNORECASE)
    block_content = (
        content_after_start[:block_end_match.start()].strip()
        if block_end_match
        else content_after_start.strip()
    )

    lines = block_content.split("\n")
    data = []

    filter_patterns = [
        r"(?i)^TEK DÜZEN.*",
        r"^\s*AKTİF\s*$",
        r"^\s*PASİF\s*$",
        r"^\s*Açıklama.*",
        r"^\s*\(?\d{4}\)?(?:\s*\(?\d{4}\)?)*\s*$",
        r"^\s*Cari Dönem\s*$",
        r"^\s*HESAP KODU.*",
        r"^\s*Enflasyon Düzeltmesi.*$",
    ]

    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if debug:
                print(f"[{block_name}] {idx}: boş satır atlandı")
            continue

        if any(re.search(pat, line_stripped) for pat in filter_patterns):
            if debug:
                print(f"[{block_name}] {idx}: header/önemsiz satır atlandı -> {line_stripped}")
            continue

        all_numeric_strings = re.findall(r"\d[\d\.\,]*", line_stripped)
        if not all_numeric_strings:
            if debug:
                print(f"[{block_name}] {idx}: sayı bulunamadı -> {line_stripped}")
            continue

        numeric_values_float = [to_float_turkish(s) for s in all_numeric_strings]
        if not any(val is not None for val in numeric_values_float):
            if debug:
                print(f"[{block_name}] {idx}: sayılar float çevrilemedi -> {line_stripped}")
            continue
        

        
        # Normal işleme devam
        # --- Sütun sayısını dinamik belirle ---
        if len(numeric_values_float) >= 3:
            # Muhtemelen enflasyonlu 3 sütun
            onceki_val, cari_val, inflation_val = numeric_values_float[-3:]
            has_inflation_column_from_header = True  # 🔥 header'dan bağımsız olarak set et
        elif len(numeric_values_float) == 2:
            onceki_val, cari_val = numeric_values_float[-2:]
            inflation_val = None
        else:
            cari_val = numeric_values_float[-1] if numeric_values_float else None
            onceki_val = inflation_val = None

        
        
        
        description, onceki_val, cari_val, inflation_val = parse_numeric_columns(line_stripped)
        
        kod = find_account_code(block_name, description)
        data.append([
            kod,
            description,
            onceki_val,
            cari_val,
            inflation_val if has_inflation_column_from_header else None
        ])

        if debug:
            print(f"[{block_name}] {idx}: eklendi -> {description} | {onceki_val}, {cari_val}, {inflation_val}")

    columns = ["Kod", "Açıklama", "Önceki Dönem", "Cari Dönem"]
    if has_inflation_column_from_header:
        columns.append("Cari Dönem (Enflasyonlu)")

    df = pd.DataFrame(data, columns=columns)
    return df, has_inflation_column_from_header



def get_bilanco_total_from_text(full_text, block_name="AKTİF"):
    """
    PDF metninden belirli bir bilanço bloğunun (AKTİF veya PASİF) TOPLAM değerlerini doğrudan ayıklar.
    """
    total_line_pattern = (
        rf"(?i){block_name}\s*TOPLAMI\s*"
        rf"({num_val_pattern_str}(?:\s+{num_val_pattern_str})?(?:\s+{num_val_pattern_str})?)"
    )
    total_match = re.search(total_line_pattern, full_text, re.DOTALL | re.IGNORECASE)

    totals = {"onceki": 0, "cari": 0, "cari_enflasyon": 0}
    if total_match:
        numeric_strings = find_all_nums_in_line.findall(total_match.group(1))
        numeric_values = [
            to_float_turkish(s) for s in numeric_strings if to_float_turkish(s) is not None
        ]

        if len(numeric_values) >= 3:
            totals["onceki"], totals["cari"], totals["cari_enflasyon"] = numeric_values[:3]
        elif len(numeric_values) == 2:
            totals["onceki"], totals["cari"] = numeric_values
        elif len(numeric_values) == 1:
            totals["cari"] = numeric_values[0]

    return totals


def parse_bilanco_from_pdf(pdf_path: str) -> dict:
    import pdfplumber, re
    from flask import current_app

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])

        # === Geliştirilmiş AKTİF / PASİF ayrımı ===
        if "PASİF" in full_text and "AKTİF" in full_text:
            aktif_text, rest_text = re.split(r"PASİF\s*(?:\n|$)", full_text, 1)
            pasif_text = re.split(r"(?i)(PASİF\s*TOPLAMI|GELİR\s*TABLOSU)", rest_text, 1)[0]
        else:
            # Bazı PDF’lerde PASİF başlığı yok — AKTİF TOPLAMI’ndan sonrasını al
            split_match = re.split(r"AKTİF\s*TOPLAMI[^\n]*\n", full_text, 1)
            if len(split_match) > 1:
                aktif_text, pasif_text = split_match[0], split_match[1]
            else:
                aktif_text = full_text
                pasif_text = ""

        # PASİF başlığı yoksa yapay olarak ekle
        if "PASİF" not in pasif_text.upper() and "III." in pasif_text:
            pasif_text = "PASİF\n" + pasif_text

        current_app.logger.info("PASİF metin örneği:\n%s", "\n".join(pasif_text.splitlines()[:30]))

    # Mükellef bilgileri
    muk = extract_mukellef_bilgileri(full_text)
    unvan = muk.get("unvan", "Bilinmiyor")
    donem = muk.get("donem", "Bilinmiyor")
    vkn = muk.get("vergi_kimlik_no", "Bilinmiyor")

    # Aktif & Pasif tablolar
    df_aktif, has_inflation_aktif = parse_table_block(aktif_text, "AKTİF")
    df_pasif, has_inflation_pasif = parse_table_block(pasif_text, "PASİF")

    # Eğer PASİF boş geldiyse, bir de “III.” başlığıyla tekrar dene
    if df_pasif is None or df_pasif.empty:
        df_pasif, has_inflation_pasif = parse_table_block(pasif_text, "III.")

    has_inflation = has_inflation_aktif or has_inflation_pasif

    # Toplamlar
    aktif_toplamlar = get_bilanco_total_from_text(full_text, "AKTİF")
    pasif_toplamlar = get_bilanco_total_from_text(full_text, "PASİF")

    if aktif_toplamlar.get("cari_enflasyon", 0) or pasif_toplamlar.get("cari_enflasyon", 0):
        has_inflation = True

    current_app.logger.info("AKTİF DF:\n%s", df_aktif.head(10).to_string())
    current_app.logger.info("PASİF DF:\n%s", df_pasif.head(10).to_string())
    current_app.logger.info("TOPLAM: %s %s", aktif_toplamlar, pasif_toplamlar)

    aktif_list = df_aktif.to_dict(orient="records") if df_aktif is not None else []
    pasif_list = df_pasif.to_dict(orient="records") if df_pasif is not None else []

 

    # --- Sonuç döndür ---
    return {
        "tur": "bilanco",
        "vergi_kimlik_no": vkn,
        "unvan": unvan,
        "donem": donem,
        "aktif": aktif_list,
        "pasif": pasif_list,
        "has_inflation": has_inflation,
        "toplamlar": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
        "direct_totals": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
        "veriler": {
            "aktif": aktif_list,
            "pasif": pasif_list,
            "toplamlar": {"AKTİF": aktif_toplamlar, "PASİF": pasif_toplamlar},
            "has_inflation": has_inflation,
        },
    }




FIND_NUM = re.compile(r"\d{1,3}(?:[\.\s]\d{3})*(?:,\d{2})?")

# ――― Kod bulucu ――― #
def find_gelir_kodu(aciklama_raw: str) -> str:
    """
    Açıklamadan üç haneli TDHP gelir tablosu kodunu döndürür.
    Bulamazsa beste benzeyeni fuzzy eşleştirerek verir.
    """
    original = aciklama_raw.strip()

    # Başta '600 …' gibi kod yazıyorsa
    m = re.match(r"^\s*(\d{3})\s*[.\-]?\s*(.*)", original)
    if m:
        return m.group(1)

    # Grup başlıkları (A. … / I. …) ise boş döndür
    if re.match(r"^\s*([A-ZÇĞİÖŞÜ]|[IVXLCDM]+)\.\s", original.upper()):
        return ""

    temiz = re.sub(r"[^\w\s]", "", original.lower())

    best_code, best_score = "", 0.0
    for grup, kod_tanim in GELIR_TABLOSU_HESAPLARI.items():
        for kod, tanim in kod_tanim.items():
            tanim_clean = re.sub(r"[^\w\s]", "", tanim.lower())
            if temiz == tanim_clean or temiz in tanim_clean:
                return kod
            # çok alakasız uzunluk farklarını at
            if abs(len(temiz) - len(tanim_clean)) > 20:
                continue
            score = difflib.SequenceMatcher(None, temiz, tanim_clean).ratio()
            if score > best_score and score > 0.75:
                best_code, best_score = kod, score
    return best_code

# ――― Koddan grup adı ――― #
def koddan_grup_bul(kod: str) -> str:
    for grup, alt in GELIR_TABLOSU_HESAPLARI.items():
        if kod in alt:
            return grup
    return "Diğer"


def parse_gelir_from_pdf(pdf_path: str) -> dict:
    import pdfplumber, re
    from flask import current_app

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # Ortak mükellef bilgileri
    muk   = extract_mukellef_bilgileri(full_text)
    unvan = muk.get("unvan", "Bilinmiyor")
    donem = muk.get("donem", "Bilinmiyor")
    vkn   = muk.get("vergi_kimlik_no", "Bilinmiyor")

    lines = full_text.splitlines()
    collecting = False
    tablo = []

    skip_patterns = [
        r"(?i)^TEK DÜZEN.*",
        r"^\s*AKTİF\s*$", r"^\s*PASİF\s*$",
        r"^\s*Açıklama\s+Önceki Dönem\s+Cari Dönem.*",
        r"^\s*\(?\d{4}\)?(?:\s*\(?\d{4}\)?)*\s*$",
        r"^\s*Cari Dönem\s*$",
        r"^\s*HESAP KODU\s+HESAP ADI.*",
        r"^\s*Enflasyon Düzeltmesi Sonrası\s*$"
    ]

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if not collecting:
            if line.upper().startswith("GELİR TABLOSU"):
                collecting = True
            continue

        if any(re.match(pat, line) for pat in skip_patterns):
            continue

        end_found = "Dönem Net Karı veya Zararı" in line

        nums = FIND_NUM.findall(line)
        if not nums:
            if end_found:
                break
            continue

        # === Dinamik sütun eşleştirme ===
        onceki = cari = None
        if len(nums) >= 2:
            onceki = to_float_turkish(nums[-2])
            cari   = to_float_turkish(nums[-1])
        elif len(nums) == 1:
            cari   = to_float_turkish(nums[-1])

        # Son sayıları temizle
        if len(nums) >= 2:
            line_cleaned = re.sub(rf"{re.escape(nums[-2])}\s*{re.escape(nums[-1])}\s*$", "", line).strip()
        elif len(nums) == 1:
            line_cleaned = re.sub(rf"{re.escape(nums[-1])}\s*$", "", line).strip()
        else:
            line_cleaned = line.strip()

        aciklama = line_cleaned.strip(" .:-")
        kod  = find_gelir_kodu(aciklama)
        grup = koddan_grup_bul(kod)

        # Negatif değer kontrolü
        if "(-)" in aciklama or kod in NEGATIVE_GELIR_CODES:
            if onceki is not None: onceki = -abs(onceki)
            if cari is not None: cari = -abs(cari)

        tablo.append({
            "kod": kod,
            "aciklama": aciklama,
            "grup": grup,
            "onceki_donem": onceki,
            "cari_donem": cari
        })

        if end_found:
            break

    if not tablo:
        current_app.logger.warning(f"[GELİR TABLOSU] {pdf_path}: hiçbir satır bulunamadı.")

    return {
        "tur": "gelir",
        "vergi_kimlik_no": vkn,
        "unvan": unvan,
        "donem": donem,
        "tablo": tablo,
        "veriler": tablo,
    }







# --- Sabitler / Regex ---
AMT_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")

SECTION_KEYS = [
    "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "KISMİ TEVKİFAT UYGULANAN İŞLEMLER",
    "DİĞER İŞLEMLER",
    "İNDİRİMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV",
    "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM",
    "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER",
    "DİĞER İADE HAKKI DOĞURAN İŞLEMLER",
    "DİĞER BİLGİLER",
]

CANON_SECTIONS = [
    "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "KISMİ TEVKİFAT UYGULANAN İŞLEMLER",
    "DİĞER İŞLEMLER",
    "MATRAH TOPLAMI",
    "İNDİRİMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV",
    "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM",
    "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER",
    "DİĞER İADE HAKKI DOĞURAN İŞLEMLER",
    "SONUÇ",
    "DİĞER BİLGİLER",
]

SECTION_ALIASES = {
    "DİĞER İŞLEMELER": "DİĞER İŞLEMLER",
    "TEVKİFAT UYGULANMAYAN İŞLEMELER": "TEVKİFAT UYGULANMAYAN İŞLEMLER",
    "İNDİRİMİNLEDRİRİMLER": "İNDİRİMLER",
    "DİĞER İŞLİENMDLİRERİMLER": "DİĞER İŞLEMLER",
    "BU DÖNEME AİT İNDİRİLECEK KDV TUTARININ ORANLARA GÖRE DAĞILIMI": "BU DÖNEME AİT İNDİRİLECEK KDV",
}

# MATRAH BLOĞU altında göstereceğimiz üç satır
SUMMARY_REDIRECT = {
    "Hesaplanan Katma Değer Vergisi": "Hesaplanan KDV",
    "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi": "Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi",
    "Toplam Katma Değer Vergisi": "Toplam KDV",
}
# Diğer tek satırlık özet anahtarlar (çakışma olmasın diye yukarıdaki 3'lüyü burada TUTMUYORUZ)
OTHER_SUMMARY_KEYS = [
    "Önceki Dönemden Devreden İndirilecek KDV",
    "Yurtiçi Alımlara İlişkin KDV", "Yurtiçi Alım KDV",
    "Sorumlu Sıfatıyla Beyan Edilerek Ödenen KDV",
    "Satıştan İade Edilen, İşlemi Gerçekleşmeyen veya İşleminden Vazgeçilen Mal ve Hizmetler",
    "İndirimler Toplamı",
    "Bu Döneme Ait İndirilecek KDV Toplamı",
    "Tecil Edilecek Katma Değer Vergisi",
    "Bu Dönemde Ödenmesi Gereken Katma Değer Vergisi",
    "İade Edilmesi Gereken Katma Değer Vergisi", "İade Edilecek KDV",
    "Sonraki Döneme Devreden KDV",
    "Sonraki Döneme Devreden Katma Değer Vergisi",
    "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (aylık)",
    "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (kümülatif)",
]

ZERO_LIKE = {"-", "0,00", "0.00", "0,00 ₺", "0.00 ₺", "", "nan", "None", None}


def _u(s):  # normalize & upper
    return (s or "").upper().replace("İ","I").replace("Ş","S").replace("Ğ","G").replace("Ü","U").replace("Ö","O").replace("Ç","C")

def classify_section(key: str) -> str:
    u = _u(key).strip()  # Türkçe harfleri ASCII’ye normalize ettik

    if key.startswith("§ "):
        return key[2:].strip()

    if u.startswith("TEVKIFATSIZ"):
        return "TEVKİFAT UYGULANMAYAN İŞLEMLER"
    
    if "KDVGUT" in u or "I/C-" in u:
        return "KISMİ TEVKİFAT UYGULANAN İŞLEMLER"

    if "KDV ORANI" in u or "TEVKIFAT ORANI" in u:
        return "KISMİ TEVKİFAT UYGULANAN İŞLEMLER"
    
    if u.startswith("DIGER HIZMETLER") or "DIGER HIZMETLER" in u:
        return "KISMİ TEVKİFAT UYGULANAN İŞLEMLER"

    if (u.startswith("MATRAH TOPLAMI")
        or u in {
            _u("Hesaplanan KDV"),
            _u("Daha Önce İndirim Konusu Yapılan KDV’nin İlavesi"),
            _u("Toplam KDV"),
        }):
        return "MATRAH TOPLAMI"
    
    if "IADE EDILECEK KDV" in u or "IADE EDILMESI GEREKEN" in u:
        return "SONUÇ"
    
    if "INDIRIMLER TOPLAMI" in u:
        return "İNDİRİMLER"

    # İNDİRİMLER (ASCII sabitlerle karşılaştır)
    if (u.startswith("ONCEKI DONEMDEN DEVREDEN")
        or "YURTICI ALIM KDV" in u
        or "SORUMLU SIFATIYLA" in u
        or "SATISTAN IADE" in u):
        return "İNDİRİMLER"

    # BU DÖNEME AİT İNDİRİLECEK KDV
    if re.match(r"^\d{1,2}\s*-\s*(MATR|VERGI)", u) or "BU DONEME AIT INDIRILECEK KDV TOPLAMI" in u:
        return "BU DÖNEME AİT İNDİRİLECEK KDV"

    # İHRAÇ
    if u.startswith("IHRAC KAYITLI") or "IHRACATIN GERCEKLESTIGI" in u:
        return "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM"

    # TAM İSTİSNA
    if ("TESLIM VE HIZMET TUTARI" in u
        or "YUKLENILEN KDV" in u
        or "KDV ODEMEKSIZIN" in u):
        return "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER"

    # DİĞER İADE HAKKI
    if u.endswith("IADEYE KONU OLAN KDV") or u.endswith("TESLIM BEDELI"):
        return "DİĞER İADE HAKKI DOĞURAN İŞLEMLER"

    if "SONRAKI DONEME DEVREDEN" in u:
        return "SONUÇ"
    
    # SONUÇ
    if u.startswith("TECIL EDILECEK") or u.startswith("BU DONEMDE ODENMESI"):
        return "SONUÇ"

    # DİĞER BİLGİLER: yalnızca iki satır
    if (u.startswith("TESLIM VE HIZMETLERIN KARSILIGINI TESKIL EDEN BEDEL (AYLIK)")
        or u.startswith("TESLIM VE HIZMETLERIN KARSILIGINI TESKIL EDEN BEDEL (KUMULATIF)")):
        return "DİĞER BİLGİLER"

    # DİĞER İŞLEMLER
    if any(s in u for s in [
        "ALINAN MALLARIN IADESI", "AMORT", "GERCEKLESMEYEN",
        "MAKINE", "TECHIZAT", "DEMIRBAS", "SATISLARI",
        "TASINMAZ", "TASIT", "ARACLARI"
    ]):
        return "DİĞER İŞLEMLER"

    return "DİĞER İŞLEMLER"



def reorder_by_section(kdv_data: dict) -> "OrderedDict[str, dict]":
    # 1) Satırları kovala
    buckets = {sec: [] for sec in CANON_SECTIONS}
    orphans = []  # hiçbir bölüme düşmeyenler
    for key in kdv_data:
        if key.startswith("§ "):
            continue
        sec = classify_section(key)
        if sec in buckets:
            buckets[sec].append(key)
        else:
            orphans.append(key)

    # 2) Kanonik sırada yeni dict oluştur
    out = OrderedDict()
    for sec in CANON_SECTIONS:
        header_key = f"§ {sec}"
        if buckets.get(sec) or header_key in kdv_data:
            out[header_key] = kdv_data.get(header_key, {})
            for row_key in buckets.get(sec, []):
                out[row_key] = kdv_data[row_key]

    # 3) Orphan satırları da geldikleri sırayla ekle (kaybolmasınlar)
    for row_key in orphans:
        out[row_key] = kdv_data[row_key]

    return out

def normalize_row_key(key: str) -> str:
    if key.startswith("§ "):
        return key

    u = _u(key)

    # --- Alınan Malların İadesi (farklı yazımları birleştir) ---
    if "ALINAN MALLARIN IADESI" in u:
        if "MATR" in u:
            return "Alınan Malların İadesi - Matrah"
        if "VERG" in u:
            return "Alınan Malların İadesi - Vergi"

    # --- Amortisman / Sabit kıymet satışları ---
    if "AMORTIS" in u or "SABIT KIYMET" in u or "MAKINE" in u:
        if "MATR" in u:
            return "Amortismana Tabi Sabit Kıymet - Matrah"
        if "VERG" in u:
            return "Amortismana Tabi Sabit Kıymet - Vergi"

    # --- Diğer Hizmetler (KDVGUT) ---
    if "DIGER HIZMETLER" in u and "MATR" in u:
        return "Diğer Hizmetler - Matrah"
    if "DIGER HIZMETLER" in u and "KDV ORANI" in u:
        return "Diğer Hizmetler - KDV Oranı"
    if "DIGER HIZMETLER" in u and "TEVKIFAT ORANI" in u:
        return "Diğer Hizmetler - Tevkifat Oranı"
    if "DIGER HIZMETLER" in u and "VERG" in u:
        return "Diğer Hizmetler - Vergi"

    return key



def consolidate_kdv_rows(kdv_data: dict) -> dict:
    """Aynı kanonik başlığa düşen satırları birleştirir (ay bazında ilk dolu değer korunur)."""
    out = {}
    for key, cols in kdv_data.items():
        canon = normalize_row_key(key)
        dest = out.setdefault(canon, {})
        # sütunları birleştir
        for m, v in cols.items():
            v = "" if v is None else str(v)
            if not dest.get(m) or str(dest[m]).strip() in ("", "nan", "None", "-"):
                dest[m] = v
            # her iki tarafta da dolu ve farklıysa istersen burada toplamayı deneyebilirsin
            # yoksa ilk geleni koruyoruz
    return out


# --- Yardımcılar ---
def _strip_diacritics(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))

def _canon(s: str) -> str:
    s = _strip_diacritics(s)
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

# Ay adını (Türkçe farklı yazımlar dahil) → sayıya çevir
def mon2num(mon: str) -> int:
    m = mon.upper().strip()
    m = (m
         .replace("Ş","S").replace("Ğ","G").replace("İ","I").replace("Ü","U").replace("Ö","O").replace("Ç","C"))
    MAP = {
        "OCAK":1, "SUBAT":2, "MART":3, "NISAN":4, "MAYIS":5, "HAZIRAN":6,
        "TEMMUZ":7, "AGUSTOS":8, "EYLUL":9, "EKIM":10, "KASIM":11, "ARALIK":12
    }
    return MAP.get(m, 99)  # eşleşmezse sona at

def month_key(col: str):
    # col: "YYYY/AY" formatında
    try:
        yil_str, ay_str = col.split("/", 1)
        return (int(yil_str), mon2num(ay_str))
    except Exception:
        return (9999, 99)


def parse_kdv_from_pdf(pdf_path):
    data, donem_adi, unvan, vkn = [], "Bilinmiyor", "Bilinmiyor", "Bilinmiyor"
    
    def norm(s): return re.sub(r"\s+", " ", s).strip()
    def amt(s):
        m = AMT_RE.search(s)
        return m.group(1) if m else "0,00"

    def add_header(title):
        data.append({"alan": f"§ {title}", "deger": "", "tip": "header"})

    def add_row(name, value="", kind="data"):
        data.append({"alan": name, "deger": value, "tip": kind})

    def ensure_header(title):
        for i in range(len(data) - 1, -1, -1):
            if data[i].get("tip") == "header":
                if data[i]["alan"] == f"§ {title}":
                    return
                break
        add_header(title)

    def find_section(u_line: str):
        # u_line burada zaten _canon(line) olmalı (büyük harf/normalize)
        for k in SECTION_KEYS:
            if u_line == _canon(k):          # TAM eşleşme
                return k
        for wrong, right in SECTION_ALIASES.items():
            if u_line == _canon(wrong):      # TAM eşleşme
                return right
        return None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print("DEBUG: Açılıyor:", pdf_path)
            full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            print("DEBUG: İlk 500 karakter:\n", full_text[:500])
            
            if "KURUMLAR VERGİSİ BEYANNAMESİ" in full_text.upper():
                return {
                    "tur": "kurumlar",
                    "donem": "Bilinmiyor",
                    "unvan": "Bilinmiyor",
                    "vergi_kimlik_no": "Bilinmiyor",
                    "veriler": [],
                    "hata": "Bu dosya Kurumlar Vergisi beyannamesi, KDV değil."
                }
            
            # DEBUG ekledik
            print("=== DEBUG PDF TEXT START ===")
            print(full_text)
            print("=== DEBUG PDF TEXT END ===")
            
            muk = extract_mukellef_bilgileri(full_text)
            unvan = muk["unvan"]
            donem_adi = muk["donem"]
            vkn = muk["vergi_kimlik_no"]

            cur_sec = None
            other_hdr_added = False
            in_matrah_block = False  # <-- yeni bayrak
            SUM_CANON = { _canon(k): v for k, v in SUMMARY_REDIRECT.items() }            


            for page in pdf.pages:
                lines = (page.extract_text() or "").split("\n")
                consumed = set()         
                pending_desc = ""     
                
                
                for i, line in enumerate(lines):
                    if i in consumed:
                        continue
                    
                    U = _canon(line)

                    # --- MATRAH BLOĞU: Matrah Toplamı + (Hesaplanan / İlave / Toplam KDV) ---
                    if _canon("Matrah Toplamı") in U:
                        ensure_header("MATRAH TOPLAMI")
                        add_row("Matrah Toplamı", amt(line))
                        in_matrah_block = True
                        continue

                    if in_matrah_block:
                        matched_summary = False
                        for k_can, shown_name in SUM_CANON.items():
                            if k_can in U:
                                ensure_header("MATRAH TOPLAMI")
                                add_row(shown_name, amt(line))
                                matched_summary = True
                                break
                        if matched_summary:
                            continue
                    # --- SON: MATRAH BLOĞU ---

                    # Matrah toplamı ayrı görünse de bu satırı ayrıca yakala (bazı PDF'lerde üstte olmayabilir)
                    if "MATRAH TOPLAMI" in U:
                        ensure_header("MATRAH TOPLAMI")
                        add_row("Matrah Toplamı", amt(line))
                        in_matrah_block = True  # takip eden üçlü için
                        continue

                    # SONUÇ bloğu
                    if "TECIL EDILECEK KATMA DEGER VERGISI" in U:
                        ensure_header("SONUÇ")
                        add_row("Tecil Edilecek Katma Değer Vergisi", amt(line))
                    if "BU DONEMDE ODENMESI GEREKEN KATMA DEGER VERGISI" in U:
                        ensure_header("SONUÇ")
                        add_row("Bu Dönemde Ödenmesi Gereken Katma Değer Vergisi", amt(line))
                        continue

                    # "Diğer İşlemler" tablo başlığına benzer bir header görülürse
                    if all(x in U for x in ["ISLEM", "TURU", "MATRAH", "VERG"]):
                        ctx = " ".join(_canon(l) for l in lines[max(0, i-2): i+3])
                        if _canon("DİĞER İŞLEMLER") in ctx:
                            if not other_hdr_added:
                                add_header("DİĞER İŞLEMLER")
                                other_hdr_added = True
                            cur_sec = "DİĞER İŞLEMLER"
                            in_matrah_block = False
                            continue

                    # Bölüm tespiti
                    sec = find_section(U)
                    if sec:
                        in_matrah_block = False
                        pending_desc = ""          
                        cur_sec = sec
                        add_header(sec)
                        if sec == "DİĞER İŞLEMLER": other_hdr_added = True
                        continue

                    # --- TEVKİFATSIZ ---
                    if cur_sec == "TEVKİFAT UYGULANMAYAN İŞLEMLER":
                        m = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                        for matrah, oran, vergi in m:
                            add_row(f"Tevkifatsız İşlem (%{oran}) - Matrah", matrah)
                            add_row(f"Tevkifatsız İşlem (%{oran}) - Vergi", vergi)
                        continue

                    # --- KISMİ TEVKİFAT ---
                    if cur_sec == "KISMİ TEVKİFAT UYGULANAN İŞLEMLER":
                        # 1) Tek satır dene
                        mk = re.search(
                            r"^(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2})\s+(\d+/\d+)\s+(\d{1,3}(?:\.\d{3})*,\d{2})$",
                            line
                        )
                        if mk:
                            desc = norm(mk.group(1))
                            add_row(f"{desc} - Matrah", mk.group(2))
                            add_row(f"{desc} - KDV Oranı", f"{mk.group(3)}%")
                            add_row(f"{desc} - Tevkifat Oranı", mk.group(4))
                            add_row(f"{desc} - Vergi", mk.group(5))
                            continue

                        # 2) Çok satır (satır kırılmalı PDF'ler): i..i+4 penceresini birleştir ve çapayı kaldır
                        window_lines = lines[i:i+5]
                        window = " ".join(window_lines)
                        mk2 = re.search(
                            r"(.*?)\s+"                                   # açıklama
                            r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"            # matrah
                            r"(\d{1,2})\s+"                              # kdv oranı
                            r"(\d+/\d+)\s+"                              # tevkifat oranı
                            r"(\d{1,3}(?:\.\d{3})*,\d{2})",              # vergi
                            window
                        )
                        if mk2:
                            desc = norm(mk2.group(1))
                            vergi_str  = mk2.group(5)
                            add_row(f"{desc} - Matrah", mk2.group(2))
                            add_row(f"{desc} - KDV Oranı", f"{mk2.group(3)}%")
                            add_row(f"{desc} - Tevkifat Oranı", mk2.group(4))
                            add_row(f"{desc} - Vergi", vergi_str)

                            # Pencerede verginin geçtiği satır indeksini bul → onu da tüket
                            end_offset = 0
                            for j, wl in enumerate(window_lines):
                                if vergi_str in wl:
                                    end_offset = j
                                    break
                            for k in range(1, end_offset+1):
                                consumed.add(i+k)
                            continue



                    # AMORTİSMAN/İADE gibi satırlar bazı PDF’lerde "Diğer İşlemler"e denktir
                    if cur_sec != "DİĞER İŞLEMLER" and re.search(r"(ALINAN MALLARIN İADESI|AMORT[Iİ]S?MAN)", _strip_diacritics(line), re.I):
                        nums_tmp = AMT_RE.findall(line)
                        if len(nums_tmp) >= 2:
                            if not other_hdr_added:
                                add_header("DİĞER İŞLEMLER")
                                other_hdr_added = True
                            cur_sec = "DİĞER İŞLEMLER"

                    # --- DİĞER İŞLEMLER (satırı parçala + devam satırı yakala) ---
                    # --- DİĞER İŞLEMLER (tek satıra düşür + güvenli ileri bakış) ---
                    if cur_sec == "DİĞER İŞLEMLER":
                        # tablo başlığı ise geç
                        if re.search(r"İşlem\s+Türü.*Matrah.*Vergi", line, re.I):
                            continue

                        nums = AMT_RE.findall(line)
                        desc_part = norm(AMT_RE.sub("", line))

                        BOUNDARY_TOKENS = (
                            "MATRAH TOPLAMI", "HESAPLANAN", "TOPLAM", "İNDİRİM", "INDIRIM",
                            "SONUÇ", "SONUC", "İŞLEMLER", "ISLEMLER", "İHRAÇ", "IHRAC",
                            "TAM İSTİSNA", "TAM ISTISNA", "BU DONEME AIT INDIRILECEK"
                        )

                        # 1) Bu satırda açıklama + 2 sayı var → hemen yaz
                        if len(nums) == 2 and desc_part:
                            full_desc = desc_part.strip()
                            # açıklama virgülle bitiyorsa ve bir sonraki satır metinse, ekle
                            j = i + 1
                            while j < len(lines):
                                if AMT_RE.search(lines[j]):  # rakam geldiyse bırak
                                    break
                                U2 = _canon(lines[j])
                                if any(tok in U2 for tok in BOUNDARY_TOKENS):
                                    break
                                nxt_desc = norm(AMT_RE.sub("", lines[j]))
                                if not nxt_desc:
                                    break
                                if full_desc.endswith(",") or full_desc.endswith(" ve") or len(full_desc) < 40:
                                    full_desc = (full_desc + " " + nxt_desc).strip()
                                    consumed.add(j)
                                    j += 1
                                    continue
                                break

                            add_row(f"{full_desc} - Matrah", nums[0])
                            add_row(f"{full_desc} - Vergi",  nums[1])
                            pending_desc = ""
                            continue

                        # 2) Sadece açıklama var (kırılmış satır) → metin devamlarını topla, sonra
                        # ilk UYGUN sayı satırından tutarları al
                        if desc_part and not nums:
                            full_desc = (pending_desc + " " + desc_part).strip() if pending_desc else desc_part

                            j = i + 1
                            while j < len(lines):
                                # sınır/özet satırına geliyorsak burada bırak (sayı almaya çalışma)
                                U2 = _canon(lines[j])
                                if any(tok in U2 for tok in BOUNDARY_TOKENS):
                                    pending_desc = full_desc  # belki sonraki sayfa/satırlarda rakam gelir
                                    break

                                if AMT_RE.search(lines[j]):        # ilk rakamlı satır
                                    nums2 = AMT_RE.findall(lines[j])
                                    if nums2:                       # 1 veya 2 sayı olabilir
                                        add_row(f"{full_desc} - Matrah", nums2[0])
                                        add_row(f"{full_desc} - Vergi",  nums2[1] if len(nums2) > 1 else "0,00")
                                        consumed.add(j)
                                        pending_desc = ""
                                    break

                                # hâlâ metin → devam cümlesi
                                nxt_desc = norm(AMT_RE.sub("", lines[j]))
                                if nxt_desc:
                                    full_desc = (full_desc + " " + nxt_desc).strip()
                                    consumed.add(j)
                                j += 1
                            continue




                    # --- TEK SATIRLIK DİĞER ÖZETLER (normalize ederek) ---
                    canon_line = _canon(line)
                    match = next((k for k in OTHER_SUMMARY_KEYS if _canon(k) in canon_line), None)
                    if match:
                        key = {
                            "Yurtiçi Alımlara İlişkin KDV": "Yurtiçi Alım KDV",
                            "İade Edilmesi Gereken Katma Değer Vergisi": "İade Edilecek KDV",
                            "Sonraki Döneme Devreden Katma Değer Vergisi": "Sonraki Döneme Devreden KDV",
                        }.get(match, match)

                        val = amt(line)
                        if val == "0,00":
                            la_text = " ".join(lines[i:i+4])
                            nums = AMT_RE.findall(la_text)
                            if nums:
                                val = nums[-1]
                        add_row(key, val)
                        continue



                    # --- BU DÖNEME AİT İNDİRİLECEK KDV ---
                    if cur_sec == "BU DÖNEME AİT İNDİRİLECEK KDV":
                        m = re.search(r"^(\d{1,2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", line)
                        if m:
                            add_row(f"{m.group(1)} - Matrah", m.group(2))
                            add_row(f"{m.group(1)} - Vergi",  m.group(3))
                            continue
                        if "TOPLAM" in _canon(line):
                            m2 = AMT_RE.findall(line)
                            if m2:
                                add_row("Bu Döneme Ait İndirilecek KDV Toplamı", m2[-1])
                            continue

                    # --- İHRAÇ ---
                    if cur_sec == "İHRAÇ KAYDIYLA TESLİMLERE AİT BİLDİRİM":
                        if "Teslim Bedeli" in line and "Hesaplanan KDV" in line:
                            nxt = lines[i+1] if i+1 < len(lines) else ""
                            m2 = AMT_RE.findall(nxt)
                            if len(m2) == 2:
                                add_row("İhraç Kayıtlı - Teslim Bedeli", m2[0])
                                add_row("İhraç Kayıtlı - Hesaplanan KDV", m2[1])
                        if "Tecil Edilebilir KDV" in line:
                            add_row("İhraç Kayıtlı - Tecil Edilebilir KDV", amt(line))
                        if "İhracatın Gerçekleştiği Dönemde İade Edilecek KDV" in line:
                            add_row("İhracatın Gerçekleştiği Dönemde İade Edilecek KDV", amt(line))
                        continue

                    # --- TAM İSTİSNA ---
                    if cur_sec == "TAM İSTİSNA KAPSAMINA GİREN İŞLEMLER":
                        nums = AMT_RE.findall(line)
                        if len(nums) >= 3:
                            desc = norm(AMT_RE.sub("", line))
                            add_row(f"{desc} - Teslim ve Hizmet Tutarı", nums[0])
                            add_row(f"{desc} - KDV Ödemeksizin Temin Edilen", nums[1])
                            add_row(f"{desc} - Yüklenilen KDV", nums[2])
                        continue

                    # --- DİĞER İADE HAKKI ---
                    if cur_sec == "DİĞER İADE HAKKI DOĞURAN İŞLEMLER":
                        nums = AMT_RE.findall(line)
                        if len(nums) >= 2:
                            desc = norm(AMT_RE.sub("", line))
                            add_row(f"{desc} - Teslim Bedeli", nums[0])
                            add_row(f"{desc} - İadeye Konu Olan KDV", nums[1])
                        continue
                    
                    

                    
            # pending_desc kaldıysa, sıfırla ekle
            if pending_desc:
                add_row(f"{pending_desc} - Matrah", "0,00")
                add_row(f"{pending_desc} - Vergi", "0,00")

        # Sıfır benzerlerini normalize et
        for r in data:
            if r.get("tip") == "header":
                continue
            v = str(r.get("deger","")).strip()
            if v in ZERO_LIKE or re.fullmatch(r"0+(?:[.,]0+)?(?:\s*₺)?", v):
                r["deger"] = "0,00"
                
        
        print(f"[DEBUG] {pdf_path} içinden {len(data)} satır parse edildi")


        return {"tur": muk["tur"], "donem": donem_adi, "unvan": unvan, "vergi_kimlik_no": vkn, "veriler": data}

    except Exception as e:
        import traceback
        print("PDF PARSE ERROR:", e)
        traceback.print_exc()
        return {
            "tur": "KDV",   
            "donem": "Hata",
            "unvan": "Bilinmiyor",
            "vergi_kimlik_no": "Bilinmiyor",
            "veriler": [],
            "hata": str(e)
        }
        
        
        
        

from urllib.parse import unquote

@app.route("/rapor-kdv-excel")
@login_required
def rapor_kdv_excel():
    import io, re, math
    import pandas as pd

    vkn   = request.args.get("vkn")
    unvan = request.args.get("unvan")
    raw   = request.args.get("donemler", "")
    secili_donemler = [d.strip() for d in unquote(raw).split(",") if d.strip()]

    if not vkn or not unvan or not secili_donemler:
        flash("❗ Mükellef (VKN + unvan) ve dönem(ler) seçilmelidir.", "warning")
        return redirect(url_for("raporlama"))

    kdv_data, kdv_months = {}, []

    # --- PDF verilerini topla ---
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        for donem in secili_donemler:
            c.execute("""
                SELECT b.veriler, b.donem
                FROM beyanname b
                JOIN mukellef m ON m.id = b.mukellef_id
                WHERE m.vergi_kimlik_no=? AND m.unvan=? AND b.donem=? AND b.tur='kdv'
            """, (vkn, unvan, donem))
            rows = c.fetchall()

            for row in rows:
                try:
                    decrypted_data = fernet.decrypt(row["veriler"]).decode("utf-8")
                    parsed = json.loads(decrypted_data)
                except Exception:
                    continue

                if not parsed:
                    continue

                # --- ✅ Donem bilgisini garantiye al ---
                raw_donem = parsed.get("donem") or row["donem"]
                try:
                    ay, yil = [p.strip() for p in raw_donem.split("/") if p.strip()]
                except ValueError:
                    continue

                col = f"{yil}/{ay.upper()}"
                if col not in kdv_months:
                    kdv_months.append(col)

                for rec in parsed.get("veriler", []):
                    alan, deger = rec["alan"], rec["deger"]
                    kdv_data.setdefault(alan, {})[col] = deger

    if not kdv_data:
        flash("KDV verisi bulunamadı.", "danger")
        return redirect(url_for("raporlama", vkn=vkn, unvan=unvan))
    
    kdv_months = sorted(set(kdv_months), key=month_key)
    kdv_data = consolidate_kdv_rows(kdv_data)
    kdv_data = reorder_by_section(kdv_data)
    
    df = pd.DataFrame.from_dict(kdv_data, orient="index")
    df = df.reindex(columns=kdv_months)
    df.index.name = "Açıklama"
    
    # --- Excel yazımı ---
    def looks_like_number(s: str) -> bool:
        if not s:
            return False
        s = str(s).strip()
        if "%" in s or "/" in s:  # oran veya kesir ise numeric değil
            return False
        return bool(re.fullmatch(r"[\d.,\-]+", s))

    # --- Excel yazımı ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook  = writer.book
        worksheet = workbook.add_worksheet("KDV Özeti")

        # biçimler
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#DCE6F1", "border": 1,
            "align": "center", "valign": "vcenter"
        })
        index_fmt = workbook.add_format({"align": "left", "border": 1})
        value_fmt = workbook.add_format({
            "num_format": '#,##0.00 "₺"', "align": "right", "border": 1
        })
        header_row_index_fmt = workbook.add_format({
            "bold": True, "bg_color": "#F2F2F2", "border": 1,
            "align": "left", "valign": "vcenter"
        })
        header_row_value_fmt = workbook.add_format({
            "bold": True, "bg_color": "#F2F2F2", "border": 1,
            "align": "center", "valign": "vcenter"
        })

        # üst başlık
        worksheet.write(0, 0, "Açıklama", header_fmt)
        for j, m in enumerate(kdv_months, start=1):
            worksheet.write(0, j, m, header_fmt)

        # satırlar
        for i, (index_val, row) in enumerate(df.iterrows(), start=1):
            text = str(index_val)
            is_header_row = text.lstrip().startswith("§")
            if is_header_row:
                display = re.sub(r"^\s*§\s*", "", text)
                worksheet.write(i, 0, display, header_row_index_fmt)
                for j, m in enumerate(kdv_months, start=1):
                    worksheet.write(i, j, "", header_row_value_fmt)
                continue

            worksheet.write(i, 0, text, index_fmt)
            for j, m in enumerate(kdv_months, start=1):
                cell_val = row.get(m, "")
                if looks_like_number(cell_val):
                    raw = str(cell_val).replace(".", "").replace(",", ".").strip()
                    try:
                        f = float(raw)
                        worksheet.write_number(i, j, f, value_fmt)
                        continue
                    except:
                        pass
                worksheet.write(i, j, str(cell_val), index_fmt)

        worksheet.set_column(0, 0, 48)
        worksheet.set_column(1, len(kdv_months), 18)
        worksheet.freeze_panes(1, 1)
        worksheet.autofilter(0, 0, len(df), len(kdv_months))

    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{unvan}_{vkn}_KDV_Ozeti.xlsx"
    )


@app.route("/rapor-kdv")
@login_required
def rapor_kdv():
    vkn   = request.args.get("vkn")
    unvan = request.args.get("unvan")
    secili_donemler = [d for d in request.args.get("kdv_periods", "").split(",") if d]

    if not vkn or not unvan or not secili_donemler:
        flash("❗ Mükellef (VKN + unvan) ve dönem(ler) seçilmelidir.", "warning")
        return redirect(url_for("raporlama"))

    kdv_data, kdv_months = {}, []

    # --- Verileri DB'den topla ---
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        for donem in secili_donemler:
            c.execute("""
                SELECT b.veriler, b.donem
                FROM beyanname b
                JOIN mukellef m ON m.id = b.mukellef_id
                WHERE m.vergi_kimlik_no=? AND m.unvan=? 
                  AND b.donem=? AND b.tur='kdv'
            """, (vkn, unvan, donem))
            rows = c.fetchall()

            for row in rows:
                try:
                    decrypted_data = fernet.decrypt(row["veriler"]).decode("utf-8")
                    parsed = json.loads(decrypted_data)
                except Exception:
                    continue

                if not parsed:
                    continue

                # ✅ Dönem bilgisini garantiye al
                raw_donem = parsed.get("donem") or row["donem"]
                try:
                    ay, yil = [p.strip() for p in raw_donem.split("/") if p.strip()]
                except ValueError:
                    continue

                col = f"{yil}/{ay.upper()}"
                if col not in kdv_months:
                    kdv_months.append(col)

                for rec in parsed.get("veriler", []):
                    alan, deger = rec["alan"], rec["deger"]
                    kdv_data.setdefault(alan, {})[col] = deger

    if not kdv_data:
        flash("Seçilen dönem(ler) için KDV verisi bulunamadı.", "warning")
        return redirect(url_for("raporlama", vkn=vkn, unvan=unvan))

    # Kolon sırası düzgün olsun
    kdv_months = sorted(set(kdv_months), key=month_key)
    kdv_data = consolidate_kdv_rows(kdv_data)
    kdv_data = reorder_by_section(kdv_data)

    # Boşluk temizliği
    for alan, cols in kdv_data.items():
        for m in kdv_months:
            v = cols.get(m, "")
            if v is None or str(v).strip() in ("", "nan", "none", "-"):
                cols[m] = ""

    return render_template(
        "rapor_kdv.html",
        secili_unvan=unvan,
        secili_vkn=vkn,
        secili_donemler=secili_donemler,
        kdv_data=kdv_data,
        kdv_months=kdv_months
    )





@app.route("/raporlama")
@login_required
def raporlama():
    # İstekten gelen parametreler
    vkn         = request.args.get("vkn")
    fa_years    = [y for y in request.args.get("fa_years", "").split(",") if y]
    kdv_periods = [d for d in request.args.get("kdv_periods", "").split(",") if d]
    analiz_turu = request.args.get("analiz_turu")
    
    print("👉 /raporlama çağrıldı")
    print("  vkn:", vkn)
    print("  fa_years:", fa_years)
    print("  kdv_periods:", kdv_periods)
    print("  analiz_turu:", analiz_turu)

    secili_vkn         = vkn
    secili_unvan       = None
    secili_fa_years    = fa_years
    secili_kdv_periods = kdv_periods

    unvanlar = []
    donemler = []
    grafik_listesi = []
    yuklenen_dosyalar = []

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        uid = session.get("user_id")
        c.execute(
            "SELECT vergi_kimlik_no, unvan FROM mukellef WHERE user_id=? ORDER BY unvan",
            (uid,)
        )
        unvanlar = [{"vkn": row["vergi_kimlik_no"], "unvan": row["unvan"]} for row in c.fetchall()]

        if secili_vkn:
            c.execute(
                "SELECT unvan FROM mukellef WHERE vergi_kimlik_no=? AND user_id=?",
                (secili_vkn, uid)
            )
            row = c.fetchone()
            if row:
                secili_unvan = row["unvan"]

            # Tüm dönemler
            # 🔍 Tüm dönemler + varsa önceki dönemleri de ekle
            c.execute("""
                SELECT DISTINCT b.donem
                FROM beyanname b
                JOIN mukellef m ON b.mukellef_id=m.id
                WHERE m.vergi_kimlik_no=? AND m.user_id=?
                ORDER BY b.donem DESC
            """, (secili_vkn, uid))
            rows = [row["donem"] for row in c.fetchall()]



            donemler = sorted(set(rows), reverse=True)
            print("[DEBUG] Donemler (raporlama):", donemler)

            # Geçmiş yüklenen dosyalar
            c.execute("""
                SELECT b.tur, b.veriler, b.yuklenme_tarihi, b.donem
                FROM beyanname b
                JOIN mukellef m ON b.mukellef_id=m.id
                WHERE m.vergi_kimlik_no=? AND m.user_id=?
                ORDER BY b.yuklenme_tarihi DESC
            """, (secili_vkn, uid))
            for r in c.fetchall():
                tarih = r["yuklenme_tarihi"]
                try:
                    utc_dt = datetime.strptime(tarih, "%Y-%m-%d %H:%M:%S")
                    ist_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Istanbul"))
                    tarih = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
                yuklenen_dosyalar.append({
                    "tur":   r["tur"],
                    "tarih": tarih,
                    "donem": r["donem"],
                })

            # Finansal analiz grafikleri (bilançodan)
            for donem in secili_fa_years:
                c.execute("""
                    SELECT b.veriler
                    FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id=m.id
                    WHERE m.vergi_kimlik_no=? AND m.user_id=? 
                    AND b.donem=? AND b.tur='bilanco'
                    LIMIT 1
                """, (secili_vkn, uid, donem))
                row_b = c.fetchone()
                if not row_b:
                    continue
                decrypted_data = fernet.decrypt(row_b["veriler"]).decode("utf-8")
                parsed = json.loads(decrypted_data)
                df_aktif = pd.DataFrame(parsed.get("aktif", []))
                if not df_aktif.empty and "Cari Dönem" in df_aktif.columns:
                    df_num = pd.to_numeric(df_aktif["Cari Dönem"], errors="coerce").fillna(0)
                    top6 = df_aktif.assign(_val=df_num).sort_values("_val", ascending=False).head(6)
                    grafik_listesi.append({
                        "donem": donem,
                        "labels": top6["Açıklama"].tolist(),
                        "values": top6["Cari Dönem"].tolist(),
                    })

    # KDV özeti
    # KDV özeti
    if secili_vkn and analiz_turu == "kdv" and secili_kdv_periods:
        kdv_months: list[str] = []
        kdv_data: dict[str, dict[str, str]] = {}

        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            for donem in secili_kdv_periods:
                c.execute("""
                    SELECT b.veriler, b.donem
                    FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id=m.id
                    WHERE m.vergi_kimlik_no=? AND m.user_id=? 
                    AND b.donem=? AND b.tur='kdv'
                """, (secili_vkn, uid, donem))
                rows = c.fetchall()
                if not rows:
                    continue

                for row_k in rows:
                    decrypted_data = fernet.decrypt(row_k["veriler"]).decode("utf-8")
                    parsed = json.loads(decrypted_data)
                    raw_donem = parsed.get("donem") or row_k["donem"]
                    try:
                        ay, yil = [p.strip() for p in raw_donem.split("/") if p.strip()]
                    except ValueError:
                        continue

                    col = f"{yil}/{ay.upper()}"
                    if col not in kdv_months:
                        kdv_months.append(col)

                    for rec in parsed.get("veriler", []):
                        alan, deger = rec["alan"], rec["deger"]
                        kdv_data.setdefault(alan, {})[col] = deger

        if not kdv_months:
            flash("Seçilen dönem(ler) için KDV verisi bulunamadı.", "warning")
            return redirect(url_for("raporlama", vkn=secili_vkn))

        kdv_months = sorted(set(kdv_months), key=month_key)
        kdv_data = consolidate_kdv_rows(kdv_data)
        kdv_data = reorder_by_section(kdv_data)
        

        for alan, cols in kdv_data.items():
            for m in kdv_months:
                v = cols.get(m, "")
                if v is None or str(v).strip() == "" or str(v).strip().lower() in ("nan", "none", "-"):
                    cols[m] = ""

        return render_template(
            "rapor_kdv.html",
            secili_vkn=secili_vkn,
            secili_unvan=secili_unvan,
            secili_donemler=secili_kdv_periods,
            kdv_months=kdv_months,
            kdv_data=kdv_data,
        )

    # Ana raporlama
    return render_template(
        "raporlama.html",
        mukellefler=unvanlar,
        donemler=donemler,
        secili_vkn=secili_vkn,
        secili_unvan=secili_unvan,
        secili_fa_years=secili_fa_years,
        secili_kdv_periods=secili_kdv_periods,
        analiz_turu=analiz_turu,
        yuklenen_dosyalar=yuklenen_dosyalar,
        grafik_listesi=grafik_listesi,
    )


@app.route("/tablo-mizan/<string:tur>", methods=["GET"])
@login_required
def tablo_mizan(tur):
    vkn   = request.args.get("vkn")
    donem = request.args.get("donem")

    if not (tur and vkn and donem):
        flash("❗ Eksik parametre.")
        return redirect(url_for("veri_giris"))

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # mukellef_id + unvan
        c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=?", (vkn,))
        row = c.fetchone()
        if not row:
            flash("❗ Mükellef bulunamadı.")
            return redirect(url_for("veri_giris", vkn=vkn, donem=donem))

        mid, secili_unvan = row["id"], row["unvan"]

        # mizan verisi DB’den
        c.execute("""
            SELECT veriler
            FROM beyanname
            WHERE user_id=? AND mukellef_id=? AND donem=? AND tur='mizan'
            LIMIT 1
        """, (session["user_id"], mid, donem))
        row = c.fetchone()

    if not row:
        flash("❗ Mizan verisi bulunamadı.")
        return redirect(url_for("veri_giris", vkn=vkn, donem=donem))

    try:
        decrypted_data = fernet.decrypt(row["veriler"]).decode("utf-8")
        mizan_data = json.loads(decrypted_data)
    except Exception:
        flash("❗ Mizan verisi okunamadı.")
        return redirect(url_for("veri_giris", vkn=vkn, donem=donem))

    donem_mapping = {"cari": donem}

    # --- Bilanço ---
    if tur == "bilanco":
        df_aktif = pd.DataFrame(mizan_data.get("aktif", []))
        df_pasif = pd.DataFrame(mizan_data.get("pasif", []))

        aktif_list = [(r.get("Kod", ""), r.get("Açıklama", ""), r.get("Cari Dönem")) for r in df_aktif.to_dict("records")]
        pasif_list = [(r.get("Kod", ""), r.get("Açıklama", ""), r.get("Cari Dönem")) for r in df_pasif.to_dict("records")]

        toplamlar = {
            "AKTİF": {"cari": pd.to_numeric(df_aktif["Cari Dönem"], errors="coerce").sum()},
            "PASİF": {"cari": pd.to_numeric(df_pasif["Cari Dönem"], errors="coerce").sum()},
        }

        return render_template("tablo_bilanco.html",
                               unvan=secili_unvan,
                               donem=donem,
                               aktif_list=aktif_list,
                               pasif_list=pasif_list,
                               toplamlar=toplamlar,
                               secilen_donem="cari",
                               donem_mapping=donem_mapping,
                               has_inflation=False,
                               aktif_alt_toplamlar={},
                               pasif_alt_toplamlar={})

    # --- Gelir ---
    elif tur == "gelir":
        df_gelir = pd.DataFrame(mizan_data.get("gelir", []))
        tablo_gelir_list = df_gelir.to_dict("records")

        return render_template("tablo_gelir.html",
                               tablo=tablo_gelir_list,
                               unvan=secili_unvan,
                               donem=donem,
                               donem_mapping=donem_mapping,
                               secilen_donem="cari")

    flash("❗ Geçersiz tablo türü veya mizan verisi.")
    return redirect(url_for("veri_giris", vkn=vkn, donem=donem))



# Bakiye işaretini belirleme fonksiyonları
def apply_balance_sign_bilanco(row, is_aktif):
    """Bilanço hesapları için bakiyelere doğru işareti uygular."""
    kod = row['Kod']
    if kod in NEGATIVE_BILANCO_CODES:
        if row['BORC_BAKIYE'] is not None and row['BORC_BAKIYE'] != 0:
            return -row['BORC_BAKIYE']
        elif row['ALACAK_BAKIYE'] is not None and row['ALACAK_BAKIYE'] != 0:
            return row['ALACAK_BAKIYE']
        return 0
    else:
        if is_aktif:
            return row['BORC_BAKIYE'] if row['BORC_BAKIYE'] is not None else 0
        else:
            return row['ALACAK_BAKIYE'] if row['ALACAK_BAKIYE'] is not None else 0

def get_gelir_sign_value(row):
    """Gelir tablosu hesapları için bakiyelere doğru işareti uygular."""
    kod = row['Kod']
    if kod in NEGATIVE_GELIR_CODES:
        return row['BORC_BAKIYE'] if row['BORC_BAKIYE'] is not None else -row['ALACAK_BAKIYE']
    else:
        return row['ALACAK_BAKIYE'] if row['ALACAK_BAKIYE'] is not None else -row['BORC_BAKIYE']


def calculate_group_total_and_add(target_df, group_definition_map):
    """DataFrame'deki grup ve alt grup toplamlarını hesaplayıp ilgili satırlara ekler."""
    df_working = target_df.copy()
    # df_working'deki 'Cari Dönem' sütununun adı zaten doğru olduğu için sorun yok.
    df_working['Cari Dönem'] = pd.to_numeric(df_working['Cari Dönem'], errors='coerce').fillna(0)

    group_totals = {}
    account_to_subgroup_map = {}

    for group_name, subgroups in group_definition_map.items():
        if isinstance(subgroups, dict):
            for kod_or_subgroup_name, accounts_or_desc in subgroups.items():
                if isinstance(accounts_or_desc, dict):
                    for kod_in_dict in accounts_or_desc.keys(): # Buradaki 'Kod' zaten BÜYÜK HARF
                        account_to_subgroup_map[kod_in_dict] = kod_or_subgroup_name
                else:
                    account_to_subgroup_map[kod_or_subgroup_name] = group_name

    # Önce alt grupların toplamını hesapla (sadece Kod'u olan satırlardan)
    for index, row in df_working.iterrows():
        # DÜZELTME BURADA: 'Kod' yerine 'Kod' kullanın
        kod = row['Kod']
        value = row['Cari Dönem']
        
        if kod != "" and kod in account_to_subgroup_map:
            subgroup_name = account_to_subgroup_map[kod]
            group_totals[subgroup_name] = group_totals.get(subgroup_name, 0) + value
        
        if kod == "Toplam" and value is not None:
            group_totals[row['Açıklama']] = value

    for index, row in df_working.iterrows():
        aciklama = row['Açıklama'] # Bu zaten BÜYÜK HARF
        kod = row['Kod'] # DÜZELTME BURADA: 'Kod' yerine 'Kod' kullanın

        if kod == "" and aciklama in group_totals:
            df_working.loc[index, 'Cari Dönem'] = group_totals[aciklama]
        
        if aciklama in group_definition_map:
            if isinstance(group_definition_map[aciklama], dict) and group_definition_map[aciklama]:
                ana_grup_toplami = 0
                for alt_grup_key in group_definition_map[aciklama].keys():
                    if alt_grup_key in group_totals:
                        ana_grup_toplami += group_totals.get(alt_grup_key, 0)
                df_working.loc[index, 'Cari Dönem'] = ana_grup_toplami
            elif aciklama in group_totals:
                 df_working.loc[index, 'Cari Dönem'] = group_totals[aciklama]
    return df_working


def parse_mizan_excel(excel_path):
    try:
        df_mizan_raw = pd.read_excel(excel_path, header=None)
        print(f"\n--- parse_mizan_excel DEBUG BAŞLANGICI ---")
        print(f"### DEBUG: 1. df_mizan_raw (okuma sonrası) satır sayısı: {df_mizan_raw.shape[0]}, sütunlar: {df_mizan_raw.columns.tolist()}")
        print(f"### DEBUG: 1. df_mizan_raw (okuma sonrası) ilk 5 satır:\n{df_mizan_raw.head().to_string()}")

        expected_columns_count = 6 
        if df_mizan_raw.shape[1] < expected_columns_count:
            raise ValueError(
                f"Mizan Excel dosyasında beklenen en az {expected_columns_count} sütun bulunamadı. "
                "Lütfen dosya formatını ve sütun sayısını kontrol edin."
            )
        
        df_mizan = pd.DataFrame()
        try:
            df_mizan['Kod'] = df_mizan_raw.iloc[:, 0].astype(str).str.strip()
            df_mizan['Açıklama'] = df_mizan_raw.iloc[:, 1].astype(str).str.strip()
            df_mizan['BORC'] = df_mizan_raw.iloc[:, 2].astype(str).str.strip()
            df_mizan['ALACAK'] = df_mizan_raw.iloc[:, 3].astype(str).str.strip()
            df_mizan['BORC_BAKIYE'] = df_mizan_raw.iloc[:, 4].astype(str).str.strip()
            df_mizan['ALACAK_BAKIYE'] = df_mizan_raw.iloc[:, 5].astype(str).str.strip()
        except IndexError as e:
            raise ValueError(
                "Mizan Excel dosyasında sütunlara erişimde hata oluştu. "
                "Beklenen sütun sayısı ve dizinleri Excel dosyanızla eşleşmiyor olabilir. "
                f"Lütfen Excel dosyanızın en az {expected_columns_count} sütuna sahip olduğundan emin olun. Hata: {e}"
            )
            
        print(f"### DEBUG: 2. df_mizan (manuel isimlendirme sonrası) satır sayısı: {df_mizan.shape[0]}, sütunlar: {df_mizan.columns.tolist()}")
        print(f"### DEBUG: 2. df_mizan (manuel isimlendirme sonrası) ilk 5 satır:\n{df_mizan.head().to_string()}")


        first_row_values = None
        if not df_mizan.empty:
            first_row_values = df_mizan.iloc[0]

        possible_headers_keywords = ['Kod', 'HESAP KODU', 'Açıklama', 'HESAP ADI', 'BORÇ', 'ALACAK', 'BAKİYE']
        first_row_is_header = False
        
        if first_row_values is not None:
             # Eğer Kod sütunu veya Açıklama sütununda başlık kelimelerinden biri geçiyorsa, başlık say.
             # Sadece Kod veya Açıklama'nın değil, diğer başlıkların da kontrol edilmesi daha iyi olabilir.
             # Bu kontrolü biraz daha esnek yapalım: ilk 6 sütundan herhangi birinde başlık kelimesi varsa.
             first_row_str = " ".join(str(first_row_values.get(col, '')).upper() for col in df_mizan.columns)
             if any(keyword in first_row_str for keyword in possible_headers_keywords):
                 first_row_is_header = True
             
        print(f"### DEBUG: 3. first_row_is_header: {first_row_is_header}")

        if first_row_is_header:
            df_mizan = df_mizan.iloc[1:].copy()
        
        print(f"### DEBUG: 4. df_mizan (başlık atlama sonrası) satır sayısı: {df_mizan.shape[0]}, ilk 5 satır:\n{df_mizan.head().to_string()}")

        # NaN kodları düşür (boş satırları veya geçersiz kodları temizle)
        initial_rows_before_dropna = df_mizan.shape[0]
        df_mizan.dropna(subset=['Kod'], inplace=True)
        print(f"### DEBUG: 5. df_mizan (NaN Kod düşme sonrası) satır sayısı: {df_mizan.shape[0]} (başlangıç {initial_rows_before_dropna})")

        initial_rows_before_digit_filter = df_mizan.shape[0]
        df_mizan = df_mizan[df_mizan['Kod'].str.match(r'^\d+$')]
        print(f"### DEBUG: 6. df_mizan (sadece rakamlı Kod filtreleme sonrası) satır sayısı: {df_mizan.shape[0]} (başlangıç {initial_rows_before_digit_filter})")
        print(f"### DEBUG: 6. df_mizan (sadece rakamlı Kod filtreleme sonrası) ilk 5 satır:\n{df_mizan.head().to_string()}")


        df_mizan['BORC_BAKIYE'] = df_mizan['BORC_BAKIYE'].apply(to_float_turkish)
        df_mizan['ALACAK_BAKIYE'] = df_mizan['ALACAK_BAKIYE'].apply(to_float_turkish)
        
        print(f"### DEBUG: 7. BORC_BAKIYE Dtypes: {df_mizan['BORC_BAKIYE'].dtype}")
        print(f"### DEBUG: 7. ALACAK_BAKIYE Dtypes: {df_mizan['ALACAK_BAKIYE'].dtype}")
        print(f"### DEBUG: 7. df_mizan (float dönüşüm sonrası) ilk 5 satır:\n{df_mizan.head().to_string()}")


        # SADECE 3 HANELİ HESAP KODLARINI FİLTRELE ve Tekilleştir
        initial_rows_before_3digit_filter = df_mizan.shape[0]
        df_filtered_3_digit_codes = df_mizan[df_mizan['Kod'].str.match(r'^\d{3}$')]
        print(f"### DEBUG: 8. df_filtered_3_digit_codes (3 haneli kod filtreleme sonrası) satır sayısı: {df_filtered_3_digit_codes.shape[0]} (başlangıç {initial_rows_before_3digit_filter})")
        print(f"### DEBUG: 8. df_filtered_3_digit_codes ilk 5 satır:\n{df_filtered_3_digit_codes.head().to_string()}")

        if df_filtered_3_digit_codes.empty:
            print("### DEBUG: 9. HİÇ 3 HANELİ HESAP KODU BULUNAMADI! Fonksiyon boş veri döndürecek.")
            return {
                "aktif": pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem']),
                "pasif": pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem']),
                "gelir": pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem']),
                "has_inflation": False,
                "unvan": "Bilinmiyor",
                "donem": "Bilinmiyor"
            }

        # Aynı 3 haneli hesap koduna sahip satırların bakiyelerini topla ve tekilleştir
        initial_rows_before_unique = df_filtered_3_digit_codes.shape[0]
        df_unique_3_digit_accounts = df_filtered_3_digit_codes.groupby('Kod').agg({
            'Açıklama': 'first',
            'BORC': 'sum',
            'ALACAK': 'sum',
            'BORC_BAKIYE': 'sum',
            'ALACAK_BAKIYE': 'sum'
        }).reset_index()
        print(f"### DEBUG: 10. df_unique_3_digit_accounts (tekilleştirme sonrası) satır sayısı: {df_unique_3_digit_accounts.shape[0]} (başlangıç {initial_rows_before_unique})")
        print(f"### DEBUG: 10. df_unique_3_digit_accounts ilk 5 satır:\n{df_unique_3_digit_accounts.head().to_string()}")

        df_unique_3_digit_accounts = df_unique_3_digit_accounts.sort_values(by='Kod')

        aktif_hesaplar = df_unique_3_digit_accounts[df_unique_3_digit_accounts['Kod'].str.startswith(('1', '2'))].copy()
        pasif_hesaplar = df_unique_3_digit_accounts[df_unique_3_digit_accounts['Kod'].str.startswith(('3', '4', '5'))].copy()
        gelir_hesaplar = df_unique_3_digit_accounts[df_unique_3_digit_accounts['Kod'].str.startswith(('6', '7'))].copy()

        print(f"### DEBUG: 11. aktif_hesaplar satır sayısı: {aktif_hesaplar.shape[0]}, ilk 5:\n{aktif_hesaplar.head().to_string()}")
        print(f"### DEBUG: 11. pasif_hesaplar satır sayısı: {pasif_hesaplar.shape[0]}, ilk 5:\n{pasif_hesaplar.head().to_string()}")
        print(f"### DEBUG: 11. gelir_hesaplar satır sayısı: {gelir_hesaplar.shape[0]}, ilk 5:\n{gelir_hesaplar.head().to_string()}")


        aktif_hesaplar['Cari Dönem'] = aktif_hesaplar.apply(lambda row: apply_balance_sign_bilanco(row, True), axis=1)
        pasif_hesaplar['Cari Dönem'] = pasif_hesaplar.apply(lambda row: apply_balance_sign_bilanco(row, False), axis=1)
        gelir_hesaplar['Cari Dönem'] = gelir_hesaplar.apply(get_gelir_sign_value, axis=1)

        print(f"### DEBUG: 12. aktif_hesaplar (Cari Dönem sonrası) ilk 5:\n{aktif_hesaplar.head().to_string()}")
        print(f"### DEBUG: 12. pasif_hesaplar (Cari Dönem sonrası) ilk 5:\n{pasif_hesaplar.head().to_string()}")
        print(f"### DEBUG: 12. gelir_hesaplar (Cari Dönem sonrası) ilk 5:\n{gelir_hesaplar.head().to_string()}")

        # Finansal Tabloları Oluşturma (Sadece Mizanda Olanları Dahil Etme)
        df_bilanco_aktif_final = pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem'])
        for grup_adi, alt_gruplar in BILANCO_HESAPLARI["AKTİF"].items():
            df_bilanco_aktif_final = pd.concat([df_bilanco_aktif_final, pd.DataFrame([{"Kod": "", "Açıklama": grup_adi, "Cari Dönem": None}])], ignore_index=True)
            for alt_grup_adi, kod_dict in alt_gruplar.items():
                df_bilanco_aktif_final = pd.concat([df_bilanco_aktif_final, pd.DataFrame([{"Kod": "", "Açıklama": alt_grup_adi, "Cari Dönem": None}])], ignore_index=True)
                for kod, aciklama in kod_dict.items():
                    hesap_satiri = aktif_hesaplar[aktif_hesaplar['Kod'] == kod]
                    if not hesap_satiri.empty:
                        df_bilanco_aktif_final = pd.concat([df_bilanco_aktif_final, hesap_satiri[['Kod', 'Açıklama', 'Cari Dönem']]], ignore_index=True)

        print(f"### DEBUG: 13. df_bilanco_aktif_final satır sayısı: {df_bilanco_aktif_final.shape[0]}, ilk 5:\n{df_bilanco_aktif_final.head().to_string()}")

        df_bilanco_pasif_final = pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem'])
        for grup_adi, alt_gruplar in BILANCO_HESAPLARI["PASİF"].items():
            df_bilanco_pasif_final = pd.concat([df_bilanco_pasif_final, pd.DataFrame([{"Kod": "", "Açıklama": grup_adi, "Cari Dönem": None}])], ignore_index=True)
            for alt_grup_adi, kod_dict in alt_gruplar.items():
                df_bilanco_pasif_final = pd.concat([df_bilanco_pasif_final, pd.DataFrame([{"Kod": "", "Açıklama": alt_grup_adi, "Cari Dönem": None}])], ignore_index=True)
                for kod, aciklama in kod_dict.items():
                    hesap_satiri = pasif_hesaplar[pasif_hesaplar['Kod'] == kod]
                    if not hesap_satiri.empty:
                        df_bilanco_pasif_final = pd.concat([df_bilanco_pasif_final, hesap_satiri[['Kod', 'Açıklama', 'Cari Dönem']]], ignore_index=True)

        print(f"### DEBUG: 14. df_bilanco_pasif_final satır sayısı: {df_bilanco_pasif_final.shape[0]}, ilk 5:\n{df_bilanco_pasif_final.head().to_string()}")

        df_gelir_final = pd.DataFrame(columns=['Kod', 'Açıklama', 'Cari Dönem'])
        gelir_hesaplar_dict = gelir_hesaplar.set_index('Kod')['Cari Dönem'].to_dict()

        for grup_adi_from_map, alt_hesaplar_tanimlari in GELIR_TABLOSU_HESAPLARI.items():
            df_gelir_final = pd.concat([df_gelir_final, pd.DataFrame([{"Kod": "", "Açıklama": grup_adi_from_map, "Cari Dönem": None}])], ignore_index=True)
            
            if isinstance(alt_hesaplar_tanimlari, dict) and alt_hesaplar_tanimlari: 
                for kod_beklenen, aciklama_beklenen in alt_hesaplar_tanimlari.items():
                    if kod_beklenen in gelir_hesaplar_dict:
                        df_gelir_final = pd.concat([df_gelir_final, pd.DataFrame([{
                            "Kod": kod_beklenen,
                            "Açıklama": aciklama_beklenen,
                            "Cari Dönem": gelir_hesaplar_dict[kod_beklenen]
                        }])], ignore_index=True)
            
            # Ara toplamları hesapla ve ekle
            # Kod ve Açıklama sütun adlarının BÜYÜK harf olduğundan emin olun
            if grup_adi_from_map == "B. SATIŞ İNDİRİMLERİ (-)":
                brut_satislar = df_gelir_final[df_gelir_final['Açıklama'] == "A. BRÜT SATIŞLAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "A. BRÜT SATIŞLAR"].empty else 0
                satis_indirimleri = df_gelir_final[df_gelir_final['Açıklama'] == "B. SATIŞ İNDİRİMLERİ (-)"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "B. SATIŞ İNDİRİMLERİ (-)"].empty else 0
                net_satislar_val = brut_satislar + satis_indirimleri
                net_satislar_idx = df_gelir_final[df_gelir_final['Açıklama'] == "C. NET SATIŞLAR"].index
                if not net_satislar_idx.empty:
                    df_gelir_final.loc[net_satislar_idx[0], 'Cari Dönem'] = net_satislar_val

            if grup_adi_from_map == "D. SATIŞLARIN MALİYETİ (-)":
                net_satislar = df_gelir_final[df_gelir_final['Açıklama'] == "C. NET SATIŞLAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "C. NET SATIŞLAR"].empty else 0
                satislarin_maliyeti = df_gelir_final[df_gelir_final['Açıklama'] == "D. SATIŞLARIN MALİYETİ (-)"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "D. SATIŞLARIN MALİYETİ (-)"].empty else 0
                brut_satis_kari_val = net_satislar + satislarin_maliyeti
                brut_satis_kari_idx = df_gelir_final[df_gelir_final['Açıklama'] == "BRÜT SATIŞ KARI VEYA ZARARI"].index
                if not brut_satis_kari_idx.empty:
                    df_gelir_final.loc[brut_satis_kari_idx[0], 'Cari Dönem'] = brut_satis_kari_val
            
            if grup_adi_from_map == "E. FAALİYET GİDERLERİ (-)":
                brut_satis_kari = df_gelir_final[df_gelir_final['Açıklama'] == "BRÜT SATIŞ KARI VEYA ZARARI"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "BRÜT SATIŞ KARI VEYA ZARARI"].empty else 0
                faaliyet_giderleri = df_gelir_final[df_gelir_final['Açıklama'] == "E. FAALİYET GİDERLERİ (-)"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "E. FAALİYET GİDERLERİ (-)"].empty else 0
                faaliyet_kari_val = brut_satis_kari + faaliyet_giderleri
                faaliyet_kari_idx = df_gelir_final[df_gelir_final['Açıklama'] == "FAALİYET KARI VEYA ZARARI"].index
                if not faaliyet_kari_idx.empty:
                    df_gelir_final.loc[faaliyet_kari_idx[0], 'Cari Dönem'] = faaliyet_kari_val

            if grup_adi_from_map == "G. DİĞER FAALİYETLERDEN OLAĞAN GİDERLER VE ZARARLAR (-)":
                faaliyet_kari = df_gelir_final[df_gelir_final['Açıklama'] == "FAALİYET KARI VEYA ZARARI"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "FAALİYET KARI VEYA ZARARI"].empty else 0
                diger_gelirler = df_gelir_final[df_gelir_final['Açıklama'] == "F. DİĞER FAALİYETLERDEN OLAĞAN GELİR VE KARLAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "F. DİĞER FAALİYETLERDEN OLAĞAN GELİR VE KARLAR"].empty else 0
                diger_giderler = df_gelir_final[df_gelir_final['Açıklama'] == "G. DİĞER FAALİYETLERDEN OLAĞAN GİDERLER VE ZARARLAR (-)"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "G. DİĞER FAALİYETLERDEN OLAĞAN GİDERLER VE ZARARLAR (-)"].empty else 0
                olagan_kar_val = faaliyet_kari + diger_gelirler + diger_giderler
                olagan_kar_idx = df_gelir_final[df_gelir_final['Açıklama'] == "OLAĞAN KAR VEYA ZARAR"].index
                if not olagan_kar_idx.empty:
                    df_gelir_final.loc[olagan_kar_idx[0], 'Cari Dönem'] = olagan_kar_val

            if grup_adi_from_map == "G. FİNANSMAN GİDERLERİ (-)":
                olagan_kar = df_gelir_final[df_gelir_final['Açıklama'] == "OLAĞAN KAR VEYA ZARAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "OLAĞAN KAR VEYA ZARAR"].empty else 0
                finansman_giderleri = df_gelir_final[df_gelir_final['Açıklama'] == "G. FİNANSMAN GİDERLERİ (-)"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "G. FİNANSMAN GİDERLERİ (-)"].empty else 0
                finansman_sonrasi_kar_val = olagan_kar + finansman_giderleri
                finansman_sonrasi_kar_idx = df_gelir_final[df_gelir_final['Açıklama'] == "FİNANSMAN GİDERLERİ SONRASI KAR VEYA ZARAR"].index
                if not finansman_sonrasi_kar_idx.empty:
                    df_gelir_final.loc[finansman_sonrasi_kar_idx[0], 'Cari Dönem'] = finansman_sonrasi_kar_val
            
            if grup_adi_from_map == "J. OLAĞANDIŞI GİDER VE ZARARLAR":
                finansman_sonrasi_kar = df_gelir_final[df_gelir_final['Açıklama'] == "FİNANSMAN GİDERLERİ SONRASI KAR VEYA ZARAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "FİNANSMAN GİDERLERİ SONRASI KAR VEYA ZARAR"].empty else 0
                olaganustu_gelirler = df_gelir_final[df_gelir_final['Açıklama'] == "I. OLAĞANDIŞI GELİR VE KARLAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "I. OLAĞANDIŞI GELİR VE KARLAR"].empty else 0
                olaganustu_giderler = df_gelir_final[df_gelir_final['Açıklama'] == "J. OLAĞANDIŞI GİDER VE ZARARLAR"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "J. OLAĞANDIŞI GİDER VE ZARARLAR"].empty else 0
                donem_kari_zarari_val = finansman_sonrasi_kar + olaganustu_gelirler + olaganustu_giderler
                donem_kari_zarari_idx = df_gelir_final[df_gelir_final['Açıklama'] == "DÖNEM KARI VEYA ZARARI"].index
                if not donem_kari_zarari_idx.empty:
                    df_gelir_final.loc[donem_kari_zarari_idx[0], 'Cari Dönem'] = donem_kari_zarari_val

            if grup_adi_from_map == "K. DÖNEM KARI, VERGİ VE DİĞER YASAL YÜKÜMLÜLÜK KARŞILIĞI":
                donem_kari_zarari = df_gelir_final[df_gelir_final['Açıklama'] == "DÖNEM KARI VEYA ZARARI"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "DÖNEM KARI VEYA ZARARI"].empty else 0
                vergi_karsiliklari = df_gelir_final[df_gelir_final['Açıklama'] == "K. DÖNEM KARI, VERGİ VE DİĞER YASAL YÜKÜMLÜLÜK KARŞILIĞI"]['Cari Dönem'].iloc[0] if not df_gelir_final[df_gelir_final['Açıklama'] == "K. DÖNEM KARI, VERGİ VE DİĞER YASAL YÜKÜMLÜLÜK KARŞILIĞI"].empty else 0 
                donem_net_kari_zarari_val = donem_kari_zarari + vergi_karsiliklari
                donem_net_kari_zarari_idx = df_gelir_final[df_gelir_final['Açıklama'] == "DÖNEM NET KARI VEYA ZARARI"].index
                if not donem_net_kari_zarari_idx.empty:
                    df_gelir_final.loc[donem_net_kari_zarari_idx[0], 'Cari Dönem'] = donem_net_kari_zarari_val

        # ... (Grup ve Alt Grup Toplamlarını Hesaplama bölümü aynı kalır)
        # calculate_group_total_and_add fonksiyonunda da 'Kod' ve 'Açıklama' kullanıldığından emin olun.
        df_bilanco_aktif_final = calculate_group_total_and_add(df_bilanco_aktif_final, BILANCO_HESAPLARI["AKTİF"])
        df_bilanco_pasif_final = calculate_group_total_and_add(df_bilanco_pasif_final, BILANCO_HESAPLARI["PASİF"])
        df_gelir_final = calculate_group_total_and_add(df_gelir_final, GELIR_TABLOSU_HESAPLARI)

        unvan_from_mizan = "Bilinmiyor"
        donem_from_mizan = "Bilinmiyor"

        has_inflation = False

        return {
            "aktif": df_bilanco_aktif_final,
            "pasif": df_bilanco_pasif_final,
            "gelir": df_gelir_final,
            "has_inflation": has_inflation,
            "unvan": unvan_from_mizan,
            "donem": donem_from_mizan
        }

    except ValueError as ve:
        print(f"VERİ AYRIŞTIRMA HATASI: {ve}")
        return {"status": "error", "message": str(ve)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"MİZAN EXCEL PARSE GENEL HATASI: {e}")
        return {"status": "error", "message": f"Mizan Excel dosyası işlenirken beklenmeyen bir hata oluştu: {str(e)}"}
    
    
    # Yükleme sonrası mizan meta verisi kaydetme/güncelleme
@app.route("/kaydet-mizan-meta", methods=["POST"])
@login_required
def kaydet_mizan_meta():
    vkn   = request.form.get("vkn")
    unvan = request.form.get("unvan")
    donem = request.form.get("donem")
    file  = request.files.get("file")  # ❗ artık dosyanın kendisi geliyor

    if not all([vkn, unvan, donem, file]):
        return jsonify({
            "status": "error",
            "title": "❗ Eksik Bilgi",
            "message": "Mükellef (VKN + unvan), dönem ve dosya yüklenmelidir."
        }), 400

    belge_turu = "mizan"

    try:
        # --- BytesIO üzerinden parse et ---
        import io
        file_bytes = io.BytesIO(file.read())
        mizan_data = parse_mizan_excel(file_bytes)

        if not mizan_data or mizan_data.get("status") == "error":
            return jsonify({
                "status": "error",
                "title": "❌ Hata",
                "message": f"Mizan dosyası işlenemedi: {mizan_data.get('message', 'Bilinmeyen hata')}"
            }), 400

        # --- DB kaydı ---
        with get_conn() as conn:
            c = conn.cursor()

            # Mükellefi bul
            c.execute("SELECT id FROM mukellef WHERE vergi_kimlik_no=? AND unvan=?", (vkn, unvan))
            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "title": "❌ Mükellef Yok",
                    "message": f"{unvan} ({vkn}) için mükellef bulunamadı."
                }), 404
            mid = row["id"]

            # JSON'a dönüştür
            veriler_json = json.dumps(mizan_data, ensure_ascii=False)

            # Eğer daha önce aynı dönem için mizan varsa güncelle
            c.execute("""
                SELECT COUNT(*) FROM beyanname 
                WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?
            """, (session["user_id"], mid, donem, belge_turu))
            if c.fetchone()[0] > 0:
                c.execute("""
                    UPDATE beyanname
                    SET veriler=?, yuklenme_tarihi=CURRENT_TIMESTAMP
                    WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?
                """, (veriler_json, session["user_id"], mid, donem, belge_turu))
                conn.commit()
                message = f"{unvan} ({vkn}) - {donem} {belge_turu.upper()} başarıyla güncellendi."
            else:
                c.execute("""
                    INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler)
                    VALUES (?, ?, ?, ?, ?)
                """, (session["user_id"], mid, donem, belge_turu, veriler_json))
                conn.commit()
                message = f"{unvan} ({vkn}) - {donem} {belge_turu.upper()} başarıyla yüklendi."

            return jsonify({
                "status": "success",
                "title": "✅ Başarılı",
                "message": message
            })

    except Exception as e:
        print(f"Mizan meta verisi kaydetme hatası: {e}")
        return jsonify({
            "status": "error",
            "title": "❌ Kayıt Hatası",
            "message": f"Mizan meta verisi kaydedilirken bir hata oluştu: {str(e)}"
        }), 500






def prepare_df(df_raw, column_name):
    import pandas as pd
    from flask import current_app

    if df_raw is None or df_raw.empty:
        current_app.logger.warning(f"[prepare_df] Boş DataFrame alındı -> column_name={column_name}")
        raise ValueError("Boş tablo alındı")

    col_map = {col.lower(): col for col in df_raw.columns}
    alternatifler = {
        "cari dönem": ["cari_donem", "cari donem"],
        "önceki dönem": ["onceki_donem", "onceki donem"],
    }

    anahtar = column_name.lower()
    ana_kolon = col_map.get(anahtar)
    if not ana_kolon and anahtar in alternatifler:
        for alt in alternatifler[anahtar]:
            if alt in col_map:
                ana_kolon = col_map[alt]
                break

    onceki_kolon = None
    for alt in alternatifler["önceki dönem"]:
        if alt in col_map:
            onceki_kolon = col_map[alt]
            break

    kod_kolon = col_map.get("kod")
    aciklama_kolon = col_map.get("açıklama") or col_map.get("aciklama")

    # 🔒 Güvenli kolon kontrolü
    kolonlar = [k for k in [kod_kolon, aciklama_kolon, ana_kolon] if k]
    if not kolonlar:
        current_app.logger.error(f"[prepare_df] Gerekli kolonlar bulunamadı. Var olan sütunlar: {list(df_raw.columns)}")
        raise ValueError("Kolon eşleşmesi yapılamadı")

    df = df_raw[kolonlar].copy()

    # 🧩 --- KOLON ADLARINI STANDARTLAŞTIR ---
    rename_map = {}
    if kod_kolon: rename_map[kod_kolon] = "Kod"
    if aciklama_kolon: rename_map[aciklama_kolon] = "Açıklama"
    if ana_kolon: rename_map[ana_kolon] = "Cari Dönem"
    df.rename(columns=rename_map, inplace=True)

    # 🧩 --- ÖNCEKİ DÖNEM KOLONUNU EKLE ---
    if onceki_kolon:
        df["Önceki Dönem"] = pd.to_numeric(df_raw[onceki_kolon], errors="coerce").fillna(0)
    else:
        df["Önceki Dönem"] = 0

    # 🔢 Sayısal dönüşüm
    if "Cari Dönem" in df.columns:
        df["Cari Dönem"] = pd.to_numeric(df["Cari Dönem"], errors="coerce").fillna(0)

    # 🧭 --- KOLON SIRASI DÜZELTME ---
    if "Önceki Dönem" in df.columns and "Cari Dönem" in df.columns:
        cols = list(df.columns)
        onceki_idx = cols.index("Önceki Dönem")
        cari_idx = cols.index("Cari Dönem")
        # Eğer Cari, Öncekiden önce geldiyse sıralamayı düzelt
        if cari_idx < onceki_idx:
            ordered = ["Kod", "Açıklama", "Önceki Dönem", "Cari Dönem"]
            # varsa enflasyon sütunlarını da sona ekle
            extras = [c for c in df.columns if "enflasyon" in c.lower() and c not in ordered]
            df = df[[c for c in ordered if c in df.columns] + extras]
            current_app.logger.warning("[prepare_df] Kolon sırası ters geldi, düzeltildi.")

    current_app.logger.info(f"[prepare_df] Kolonlar: {list(df.columns)} | Satır sayısı: {len(df)}")

    return df



ALLOWED_CATEGORIES = {'likidite', 'karlilik', 'borç', 'borsa'}
ALLOWED_INFLATION = {'cari', 'cari_enflasyon'}

@app.route("/finansal-analiz", methods=["GET"])
@login_required
def finansal_analiz():
    import pandas as pd
    import math

    secili_vkn = request.args.get("vkn")
    secili_yillar = request.args.getlist("yillar")
    inflation_mode = request.args.get("inflation_mode", "auto")
    kategori = request.args.get("kategori", "likidite")
    data_source = request.args.get("data_source", "pdf")

    secili_yillar = [str(y).strip() for y in secili_yillar if y]

    unvanlar = []
    trend_data = {}
    mevcut_yillar = []
    uyarilar = []

    uid = session.get("user_id")

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # --- Mükellef listesi ---
        c.execute("""
            SELECT vergi_kimlik_no, unvan 
            FROM mukellef 
            WHERE user_id=? 
            ORDER BY unvan
        """, (uid,))
        unvanlar = [{"vkn": row["vergi_kimlik_no"], "unvan": row["unvan"]} for row in c.fetchall()]

        if secili_vkn:
            # --- Mevcut yılları çek ---
            c.execute("""
                SELECT DISTINCT b.donem
                FROM beyanname b
                JOIN mukellef m ON b.mukellef_id=m.id
                WHERE m.user_id=? AND m.vergi_kimlik_no=? 
                AND b.tur='bilanco'
                ORDER BY b.donem DESC
            """, (uid, secili_vkn))
            mevcut_yillar = [r["donem"] for r in c.fetchall()]

            if not secili_yillar:
                secili_yillar = sorted(mevcut_yillar, reverse=True)

            # --- Her yıl için analiz ---
            for yil in secili_yillar:
                try:
                    # 📄 Bilanço çek
                    c.execute("""
                        SELECT b.veriler 
                        FROM beyanname b
                        JOIN mukellef m ON b.mukellef_id=m.id
                        WHERE m.user_id=? AND m.vergi_kimlik_no=? 
                        AND b.donem=? AND b.tur='bilanco'
                        ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                    """, (uid, secili_vkn, yil))
                    bilanco_row = c.fetchone()

                    # 📄 Gelir tablosu çek
                    c.execute("""
                        SELECT b.veriler 
                        FROM beyanname b
                        JOIN mukellef m ON b.mukellef_id=m.id
                        WHERE m.user_id=? AND m.vergi_kimlik_no=? 
                        AND b.donem=? AND b.tur='gelir'
                        ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                    """, (uid, secili_vkn, yil))
                    gelir_row = c.fetchone()

                    if not bilanco_row or not gelir_row:
                        current_app.logger.warning(f"[ANALIZ] {yil} yılı verisi eksik (bilanço veya gelir yok)")
                        continue

                    # 🧩 Decrypt et
                    raw_b = fernet.decrypt(bilanco_row["veriler"]).decode("utf-8")
                    raw_g = fernet.decrypt(gelir_row["veriler"]).decode("utf-8")
                    parsed_b = json.loads(raw_b)
                    parsed_g = json.loads(raw_g)

                    if isinstance(parsed_b, list):
                        parsed_b = {"aktif": parsed_b, "pasif": []}
                    if isinstance(parsed_g, list):
                        parsed_g = {"tablo": parsed_g}

                    aktif_df = pd.DataFrame(parsed_b.get("aktif", []))
                    pasif_df = pd.DataFrame(parsed_b.get("pasif", []))
                    gelir_df = pd.DataFrame(parsed_g.get("tablo", []))

                    if aktif_df.empty or pasif_df.empty or gelir_df.empty:
                        current_app.logger.warning(f"[ANALIZ] {yil} yılı veri boş geçti.")
                        continue

                    has_inflation = "Cari Dönem (Enflasyonlu)" in aktif_df.columns

                    # 🔢 Enflasyon seçimi
                    if inflation_mode == "enflasyonlu" and has_inflation:
                        bilanco_col = "Cari Dönem (Enflasyonlu)"
                    elif inflation_mode == "enflasyonsuz":
                        bilanco_col = "Cari Dönem"
                    else:
                        bilanco_col = "Cari Dönem (Enflasyonlu)" if has_inflation else "Cari Dönem"

                    aktif_df_final = prepare_df(aktif_df, bilanco_col)
                    pasif_df_final = prepare_df(pasif_df, bilanco_col)
                    gelir_df_final = prepare_df(gelir_df, "Cari Dönem")

                    # --- 📉 Önceki yıl kayıtlarını artık DB'den çekiyoruz ---
                    prev_year = str(int(yil) - 1)

                    # Bilanço - önceki yıl
                    c.execute("""
                        SELECT veriler FROM beyanname b
                        JOIN mukellef m ON b.mukellef_id=m.id
                        WHERE m.user_id=? AND m.vergi_kimlik_no=? 
                        AND b.donem=? AND b.tur='bilanco'
                        ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                    """, (uid, secili_vkn, prev_year))
                    prev_bilanco = c.fetchone()

                    if prev_bilanco:
                        raw_prev_b = fernet.decrypt(prev_bilanco["veriler"]).decode("utf-8")
                        parsed_prev_b = json.loads(raw_prev_b)
                        aktif_df_prev = prepare_df(pd.DataFrame(parsed_prev_b.get("aktif", [])), "Cari Dönem")
                        pasif_df_prev = prepare_df(pd.DataFrame(parsed_prev_b.get("pasif", [])), "Cari Dönem")
                    else:
                        aktif_df_prev = pd.DataFrame()
                        pasif_df_prev = pd.DataFrame()

                    # Gelir - önceki yıl
                    c.execute("""
                        SELECT veriler FROM beyanname b
                        JOIN mukellef m ON b.mukellef_id=m.id
                        WHERE m.user_id=? AND m.vergi_kimlik_no=? 
                        AND b.donem=? AND b.tur='gelir'
                        ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                    """, (uid, secili_vkn, prev_year))
                    prev_gelir = c.fetchone()

                    if prev_gelir:
                        raw_prev_g = fernet.decrypt(prev_gelir["veriler"]).decode("utf-8")
                        parsed_prev_g = json.loads(raw_prev_g)
                        gelir_df_prev = prepare_df(
                            pd.DataFrame(parsed_prev_g if isinstance(parsed_prev_g, list) else parsed_prev_g.get("tablo", [])),
                            "Cari Dönem"
                        )
                    else:
                        gelir_df_prev = pd.DataFrame()

                    # --- 💹 Cari yıl oranları ---
                    oranlar_yil = hesapla_finansal_oranlar(aktif_df_final, pasif_df_final, gelir_df_final, kategori)
                    for oran, val in oranlar_yil.items():
                        deger = val["deger"] if isinstance(val, dict) and "deger" in val else val
                        trend_data.setdefault(oran, {})[yil] = deger or 0.0

                    # --- 💹 Önceki yıl oranları ---
                    if not aktif_df_prev.empty and not pasif_df_prev.empty and not gelir_df_prev.empty:
                        oranlar_prev = hesapla_finansal_oranlar(aktif_df_prev, pasif_df_prev, gelir_df_prev, kategori)
                        for oran, val in oranlar_prev.items():
                            deger = val["deger"] if isinstance(val, dict) and "deger" in val else val
                            trend_data.setdefault(oran, {})[prev_year] = deger or 0.0

                        if prev_year not in mevcut_yillar:
                            mevcut_yillar.append(prev_year)
                        if prev_year not in secili_yillar:
                            secili_yillar.append(prev_year)

                    current_app.logger.info(f"[TREND] {yil} ve {prev_year} yılları analize dahil edildi.")

                except Exception as e:
                    current_app.logger.warning(f"[TREND] {yil} verisi alınamadı: {e}", exc_info=True)

    return render_template(
        "finansal_analiz.html",
        unvanlar=unvanlar,
        secili_vkn=secili_vkn,
        kategori=kategori,
        mevcut_yillar=sorted(list(set(mevcut_yillar)), reverse=True),
        secili_yillar=sorted(list(set(secili_yillar)), reverse=True),
        inflation_mode=inflation_mode,
        trend_data=trend_data,
        uyarilar=uyarilar,
    )








@app.route("/raporlama_grafik")
@login_required
def raporlama_grafik():
    import pandas as pd
    import json
    from flask import request, render_template, current_app

    vkn = request.args.get("vkn")
    unvan = request.args.get("unvan")
    fa_years_raw = request.args.get("fa_years", "")
    secili_yillar = [d.strip() for d in fa_years_raw.split(",") if d.strip()]

    # -------------------------------------------------------------
    # 📌 1. Giriş kontrolü
    # -------------------------------------------------------------
    if not (vkn and unvan):
        return render_template(
            "raporlama_grafik.html",
            vkn="", unvan="", donemler=[],
            raporlar={}, analiz={"oran_analizleri": {}},
            default_suggestions=[], seriler={}, eksik_yillar=[]
        )

    # -------------------------------------------------------------
    # 📌 2. Mevcut dönemleri DB’den çek
    # -------------------------------------------------------------
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT b.donem
            FROM beyanname b
            JOIN mukellef m ON b.mukellef_id=m.id
            WHERE m.vergi_kimlik_no=? AND m.unvan=? 
              AND (b.tur='bilanco' OR b.tur='gelir')
            ORDER BY b.donem ASC
        """, (vkn, unvan))
        all_years = [r[0] for r in c.fetchall()]

    donemler = secili_yillar if secili_yillar else all_years
    donemler = [str(d) for d in donemler]

    raporlar = {}
    eksik_yillar = []

    # -------------------------------------------------------------
    # 📊 3. Her yıl için finansal tabloları işle
    # -------------------------------------------------------------
    for yil in donemler:
        try:
            with get_conn() as conn:
                c = conn.cursor()

                # --- Bilanço verileri
                c.execute("""
                    SELECT b.veriler FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id=m.id
                    WHERE m.vergi_kimlik_no=? AND m.unvan=? 
                    AND b.donem=? AND b.tur='bilanco'
                    ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                """, (vkn, unvan, yil))
                rb = c.fetchone()

                # --- Gelir tablosu verileri
                c.execute("""
                    SELECT b.veriler FROM beyanname b
                    JOIN mukellef m ON b.mukellef_id=m.id
                    WHERE m.vergi_kimlik_no=? AND m.unvan=? 
                    AND b.donem=? AND b.tur='gelir'
                    ORDER BY b.yuklenme_tarihi DESC LIMIT 1
                """, (vkn, unvan, yil))
                rg = c.fetchone()

            # Eğer biri yoksa eksik say
            if not rb or not rg:
                eksik_yillar.append(yil)
                continue

            # --- Bilanço PDF verisini çöz
            parsed_b = json.loads(fernet.decrypt(rb[0]).decode("utf-8"))
            aktif_raw = pd.DataFrame(parsed_b.get("aktif", []))
            pasif_raw = pd.DataFrame(parsed_b.get("pasif", []))

            has_inflation = "Cari Dönem (Enflasyonlu)" in aktif_raw.columns
            bilanco_col = "Cari Dönem (Enflasyonlu)" if has_inflation else "Cari Dönem"

            aktif_df = prepare_df(aktif_raw, bilanco_col)
            pasif_df = prepare_df(pasif_raw, bilanco_col)

            # --- Gelir tablosu PDF verisini çöz
            parsed_g = json.loads(fernet.decrypt(rg[0]).decode("utf-8"))
            if isinstance(parsed_g, list):
                gelir_raw = pd.DataFrame(parsed_g)
            elif isinstance(parsed_g, dict):
                gelir_raw = pd.DataFrame(parsed_g.get("tablo", []))
            else:
                gelir_raw = pd.DataFrame([])

            gelir_df = prepare_df(gelir_raw, "Cari Dönem")


            # --- Finansal oranları hesapla (tek merkez)
            raporlar[yil] = hesapla_finansal_oranlar(
                aktif_df, pasif_df, gelir_df, kategori="tümü"
            )

            # --- Kalemleri ekle (aktif, pasif, gelir)
            for kategori, df in [("aktif", aktif_df), ("pasif", pasif_df), ("gelir", gelir_df)]:
                for _, row in df.iterrows():
                    kod = str(row.get("Kod") or "")
                    aciklama = str(row.get("Açıklama") or "").strip()
                    key = f"{kategori}_{kod or aciklama}"
                    value = float(row.get("Cari Dönem", 0) or 0)
                    if not value:
                        continue
                    # hem raporlar hem index için ekle
                    raporlar[yil][key] = {"deger": value, "kategori": kategori, "aciklama": aciklama, "kod": kod}

        except Exception as e:
            current_app.logger.warning(f"[{yil}] veri işleme hatası: {e}")
            eksik_yillar.append(yil)
            continue

    # -------------------------------------------------------------
    # ⚠️ 4. Eğer hiç veri yoksa uyarı göster
    # -------------------------------------------------------------
    if not raporlar:
        return render_template(
            "raporlama_grafik.html",
            vkn=vkn, unvan=unvan, donemler=[],
            raporlar={}, analiz={"oran_analizleri": {}},
            default_suggestions=[], seriler={}, eksik_yillar=eksik_yillar,
            swal_warning="Oran tablosu oluşturmak için ilgili yılların bilanço ve gelir PDF’leri gerekli."
        )

    # -------------------------------------------------------------
    # 📈 5. Analiz oluştur (trend + yorum)
    # -------------------------------------------------------------
    analiz = analiz_olustur({int(y): raporlar[y] for y in raporlar})

    # -------------------------------------------------------------
    # 💡 6. Grafik varsayılan seriler (örnek)
    # -------------------------------------------------------------
    default_suggestions = []
    for w in ["Cari Oran", "Brüt Kar Marjı", "Özsermaye Karlılığı", "Aktif Karlılığı"]:
        for oran in raporlar[list(raporlar.keys())[0]].keys():
            if w.lower() in oran.lower():
                default_suggestions.append(oran)
                break

    default_suggestions = list(dict.fromkeys(default_suggestions))


    # 📊 7. Kalem indeksleri ve seriler (grafik araması için)
    # -------------------------------------------------------------
    kalem_index = []
    kalem_series = {}

    for yil, oranlar in raporlar.items():
        for oran_adi, oran_detay in oranlar.items():
            if isinstance(oran_detay, dict):
                val = oran_detay.get("deger", None)
                src = oran_detay.get("kategori", "oran")
                label = oran_adi
                kod = oran_detay.get("kod", "")
                aciklama = oran_detay.get("aciklama", oran_adi)
            else:
                val = oran_detay
                src = "oran"
                label = oran_adi
                kod = ""
                aciklama = oran_adi

            key = oran_adi
            kalem_index.append({
                "key": key,
                "label": label,
                "code": kod,
                "name": aciklama,
                "source": src
            })
            kalem_series.setdefault(key, {})[yil] = val

    # -------------------------------------------------------------
    # 🧩 8. Sayfa render
    # -------------------------------------------------------------
    return render_template(
        "raporlama_grafik.html",
        vkn=vkn, 
        unvan=unvan,
        fa_years=fa_years_raw, 
        donemler=sorted(set(donemler)),
        raporlar=raporlar,
        analiz=analiz,
        default_suggestions=default_suggestions,
        seriler=raporlar,
        eksik_yillar=eksik_yillar,
        kalem_index=kalem_index,
        kalem_series=kalem_series
    )

@app.route("/finansal-oran-raporu")
@login_required
def finansal_oran_raporu():
    import os, io, json, tempfile, shutil, pdfkit, traceback, pandas as pd
    from datetime import datetime
    from flask import current_app, render_template, request, flash, redirect, url_for, send_file, session

    vkn = request.args.get("vkn")
    donemler_raw = request.args.getlist("donemler")

    # 🧮 Dönemleri ayrıştır
    if len(donemler_raw) == 1 and "," in donemler_raw[0]:
        donemler = [d.strip() for d in donemler_raw[0].split(",") if d.strip()]
    else:
        donemler = [d.strip() for d in donemler_raw if d.strip()]

    if not (vkn and donemler):
        flash("❗ Mükellef VKN ve dönem bilgisi eksik.", "warning")
        return redirect(url_for("raporlama"))

    uid = session.get("user_id")
    reports = {}

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 🔍 Mükellef bul
        c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=? AND user_id=?", (vkn, uid))
        row = c.fetchone()
        if not row:
            flash(f"❗ {vkn} numaralı mükellef bulunamadı.", "danger")
            return redirect(url_for("raporlama"))

        mukellef_id = row["id"]
        unvan = row["unvan"]

        # 🔢 Dönem verilerini oku
        for donem in donemler:
            c.execute("""
                SELECT veriler FROM beyanname
                WHERE mukellef_id=? AND donem=? AND tur='bilanco'
                ORDER BY yuklenme_tarihi DESC LIMIT 1
            """, (mukellef_id, donem))
            bilanco_row = c.fetchone()

            c.execute("""
                SELECT veriler FROM beyanname
                WHERE mukellef_id=? AND donem=? AND tur='gelir'
                ORDER BY yuklenme_tarihi DESC LIMIT 1
            """, (mukellef_id, donem))
            gelir_row = c.fetchone()

            if not bilanco_row or not gelir_row:
                flash(f"❗ {donem} dönemi için '{unvan}' belgeleri eksik.", "danger")
                return redirect(url_for("raporlama", vkn=vkn))

            # 🧩 Decode + parse
            decrypted_b = fernet.decrypt(bilanco_row["veriler"]).decode("utf-8")
            decrypted_g = fernet.decrypt(gelir_row["veriler"]).decode("utf-8")
            b_data = json.loads(decrypted_b)
            g_data = json.loads(decrypted_g)

            if isinstance(b_data, list): b_data = {"aktif": b_data, "pasif": []}
            if isinstance(g_data, list): g_data = {"tablo": g_data}

            df_aktif = pd.DataFrame(b_data.get("aktif", []))
            df_pasif = pd.DataFrame(b_data.get("pasif", []))
            df_gelir = pd.DataFrame(g_data.get("tablo", []))

            for df in [df_aktif, df_pasif, df_gelir]:
                df.columns = [c.strip() for c in df.columns]
                df.rename(columns={
                    "Hesap Kodu": "Kod",
                    "Hesap": "Kod",
                    "Hesap No": "Kod",
                    "Kodu": "Kod",
                    "Cari Donem": "Cari Dönem",
                    "Cari Donem (TL)": "Cari Dönem",
                    "Cari Donem (Enflasyonlu)": "Cari Dönem",
                    "Cari Dönem Tutarı": "Cari Dönem",
                }, inplace=True)

            for name, df in [("aktif", df_aktif), ("pasif", df_pasif), ("gelir", df_gelir)]:
                if "Kod" not in df.columns:
                    df["Kod"] = df.index.astype(str)
                if "Cari Dönem" not in df.columns:
                    candidate = next((c for c in df.columns if "Cari" in c or "Dönem" in c or "Donem" in c or "202" in c), None)
                    if candidate:
                        df["Cari Dönem"] = df[candidate]

            tekdonem_oranlar = hesapla_finansal_oranlar(df_aktif, df_pasif, df_gelir, kategori="tümü")
            reports[int(donem)] = tekdonem_oranlar

    analiz = analiz_olustur(reports)

    # 🧾 HTML render et
    rendered = render_template(
        "pdf_finansal_oran.html",
        vkn=vkn,
        unvan=unvan,
        donemler=sorted(reports.keys()),
        reports=reports,
        analiz=analiz,
        adres="Adresinizi buraya",
        telefon="(0212) 123 45 67",
        email="info@firma.com",
        now=datetime.now
    )

    try:
        
        # 💾 HTML debug çıktısı — PDF oluşmadan önce HTML'yi kaydeder
        debug_path = os.path.join(current_app.root_path, "rendered_debug.html")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"✅ HTML debug dosyası kaydedildi: {debug_path}")
        
        wkhtml_path = current_app.config.get("WKHTMLTOPDF_PATH") or shutil.which("wkhtmltopdf")
        if not wkhtml_path or not os.path.exists(wkhtml_path):
            flash("❗ wkhtmltopdf bulunamadı.", "danger")
            return redirect(url_for("raporlama", vkn=vkn))

        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

        # 🧩 HTML'yi geçici dosyaya kaydet (CSS bu şekilde %100 uygulanır)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as html_file:
            html_file.write(rendered)
            html_path = html_file.name

        # 📄 PDF oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdfkit.from_file(
                html_path,
                tmpfile.name,
                configuration=config,
                options={
                    "page-size": "A4",
                    "encoding": "UTF-8",
                    "enable-local-file-access": None,
                    "margin-top": "15mm",
                    "margin-bottom": "15mm",
                    "margin-left": "12mm",
                    "margin-right": "12mm",
                    "dpi": 300,
                    "zoom": "1.05",
                    "print-media-type": None,
                },
            )
            tmpfile.flush()

        print("✅ PDF başarıyla oluşturuldu:", tmpfile.name)
        return send_file(
            tmpfile.name,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{vkn}_{unvan}_Oran_Raporu.pdf"
        )

    except Exception as e:
        print("🧨 PDF oluşturma hatası:", e)
        traceback.print_exc()
        flash(f"PDF oluşturulamadı: {e}", "danger")
        return redirect(url_for("raporlama", vkn=vkn))

    finally:
        try:
            if 'html_path' in locals() and os.path.exists(html_path):
                os.remove(html_path)
            if 'tmpfile' in locals() and os.path.exists(tmpfile.name):
                os.remove(tmpfile.name)
        except Exception:
            pass



@app.route("/mukellef-sil", methods=["POST"])
@login_required
def mukellef_sil():
    vkn = request.form.get("vkn", "").strip()

    if not vkn:
        return jsonify({
            "status": "error",
            "title": "❗ Hata",
            "message": "Silinecek mükellef için vergi kimlik no gerekli."
        }), 400

    try:
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # mukellef id ve unvan bul
            c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=?", (vkn,))
            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "title": "❌ Bulunamadı",
                    "message": f"VKN {vkn} için kayıtlı mükellef bulunamadı."
                }), 404
            mid, unvan = row["id"], row["unvan"]

            c.execute("DELETE FROM beyanname WHERE user_id=? AND mukellef_id=?", (session["user_id"], mid))
            c.execute("DELETE FROM mukellef WHERE user_id=? AND id=?", (session["user_id"], mid))
            conn.commit()

        return jsonify({
            "status": "success",
            "title": "✅ Başarıyla Silindi",
            "message": f"Mükellef {unvan} ({vkn}) ve tüm beyannameleri silindi."
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "title": "❌ Silme Hatası",
            "message": str(e)
        }), 500


@app.route("/donem-sil", methods=["POST"])
@login_required
def donem_sil():
    vkn        = request.form.get("vkn", "").strip()
    donem      = request.form.get("donem", "").strip()
    belge_turu = request.form.get("belge_turu", "").strip()

    if not (vkn and donem):
        return jsonify({
            "status": "error",
            "title": "❗ Hata",
            "message": "Eksik parametre gönderildi."
        }), 400

    try:
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=?", (vkn,))
            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "title": "❌ Bulunamadı",
                    "message": f"VKN {vkn} için kayıtlı mükellef bulunamadı."
                }), 404
            mid, unvan = row["id"], row["unvan"]

            if belge_turu == "all":
                c.execute("DELETE FROM beyanname WHERE user_id=? AND mukellef_id=? AND donem=?", (session["user_id"], mid, donem))
                message = f"{unvan} ({vkn}) {donem} tüm beyannameleri silindi."
            else:
                c.execute("DELETE FROM beyanname WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?", (session["user_id"], mid, donem, belge_turu))
                message = f"{unvan} ({vkn}) {donem} {belge_turu.upper()} belgesi silindi."

            conn.commit()

        return jsonify({"status": "success", "title": "✅ Başarıyla Silindi", "message": message})

    except Exception as e:
        return jsonify({"status": "error", "title": "❌ Hata", "message": str(e)}), 500


@app.route("/yeniden-yukle", methods=["POST"])
@login_required
def yeniden_yukle():
    vkn        = request.form.get("vkn")
    donem      = request.form.get("donem")
    belge_turu = request.form.get("belge_turu")
    veriler    = request.form.get("veriler")  # JSON string ya da base64/BytesIO olabilir

    if not all([vkn, donem, belge_turu, veriler]):
        return jsonify({
            "status": "error",
            "title": "❗ Eksik Bilgi",
            "message": "Eksik parametreler gönderildi."
        }), 400

    try:
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # mukellef id ve unvan bul
            c.execute("SELECT id, unvan FROM mukellef WHERE vergi_kimlik_no=?", (vkn,))
            row = c.fetchone()
            if not row:
                return jsonify({
                    "status": "error",
                    "title": "❌ Bulunamadı",
                    "message": f"VKN {vkn} için mükellef bulunamadı."
                }), 404
            mid, unvan = row["id"], row["unvan"]

            # eski kaydı sil
            c.execute("""
                DELETE FROM beyanname
                WHERE user_id=? AND mukellef_id=? AND donem=? AND tur=?
            """, (session["user_id"], mid, donem, belge_turu))

            # yeni kaydı ekle
            c.execute("""
                INSERT INTO beyanname (user_id, mukellef_id, donem, tur, veriler, yuklenme_tarihi)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (session["user_id"], mid, donem, belge_turu, veriler))

            conn.commit()

            # yüklenme tarihini oku
            c.execute("SELECT yuklenme_tarihi FROM beyanname WHERE rowid = last_insert_rowid()")
            row = c.fetchone()
            if row and row["yuklenme_tarihi"]:
                utc_dt = datetime.strptime(row["yuklenme_tarihi"], "%Y-%m-%d %H:%M:%S")
                istanbul_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Istanbul"))
                print(f"DEBUG | {unvan} ({vkn}) - {donem} {belge_turu.upper()} yeniden yüklendi: {istanbul_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        return jsonify({
            "status": "success",
            "title": "✔️ Başarıyla Güncellendi",
            "message": f"{unvan} - {donem} ({belge_turu.upper()}) başarıyla yeniden yüklendi."
        })

    except sqlite3.Error as e:
        return jsonify({
            "status": "error",
            "title": "❌ Veritabanı Hatası",
            "message": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "title": "❌ Sunucu Hatası",
            "message": str(e)
        }), 500


@app.route("/matrah", methods=["GET", "POST"])
@login_required
def matrah():
    matrah = None
    if request.method == "POST":
        gelir = float(request.form.get("gelir", 0))
        gider = float(request.form.get("gider", 0))
        matrah = gelir - gider

        # Veritabanına kaydet
        with get_conn() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO matrahlar (user, gelir, gider, matrah) VALUES (?, ?, ?, ?)",
                (session["user"], gelir, gider, matrah)
            )
            conn.commit()

    # Kayıtlı verileri getir
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT gelir, gider, matrah, tarih FROM matrahlar WHERE user = ? ORDER BY tarih DESC",
            (session["user"],)
        )
        kayitlar = c.fetchall()

    return render_template("matrah.html", matrah=matrah, kayitlar=kayitlar)

@app.route("/about")
@login_required
def about():
    return render_template("about.html")

@app.route("/team")
@login_required
def team():
    return render_template("team.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name    = request.form.get("name")
        email   = request.form.get("email")
        message = request.form.get("message")
        # Burada dilerseniz veritabanına veya e-postaya kaydedebilirsiniz
        flash("Mesajınız bize ulaştı, Teşekkürler!", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route('/asgari') # Bu kısım Flask'a '/asgari' URL'sine gelen istekleri 'asgari' fonksiyonuna yönlendirmesini söyler.
def asgari(): # Bu fonksiyonun adı 'asgari', url_for('asgari') ile eşleşen endpoint adıdır.
    # Burada asgari vergi hesaplama veya gösterme ile ilgili mantığınız olacak
    return render_template('asgari.html') # asgari.html adında bir şablonunuzun olması beklenir

@app.route('/sermaye')
def sermaye():
    # Sermaye artırımı ile ilgili mantık
    return render_template('sermaye.html')

@app.route('/finansman')
def finansman():
    # Finansman gideri ile ilgili mantık
    return render_template('finansman.html')

@app.route('/vergi_hesaplamalari')
def vergi_hesaplamalari():    
    return render_template('vergi_hesaplamalari.html')



def gelir_vergisi_hesapla(yil: int, gelir: float, tarifeler: dict, ucret: bool = False) -> float:
    tarife_yili = tarifeler.get(yil)
    if not tarife_yili:
        raise ValueError(f"{yil} yılı için tarife tanımlı değil")

    tarife_tipi = "ucret" if ucret else "normal"
    dilimler = tarife_yili.get(tarife_tipi)
    if not dilimler:
        raise ValueError(f"{yil} yılı için '{tarife_tipi}' tarifesi yok")

    vergi = 0.0

    for i in range(len(dilimler)):
        alt_limit, _, oran = dilimler[i]
        if i + 1 < len(dilimler):
            ust_limit = dilimler[i + 1][0]
        else:
            ust_limit = float("inf")

        if gelir > alt_limit:
            vergilenecek = min(gelir, ust_limit) - alt_limit
            vergi += vergilenecek * oran
        else:
            break

    return round(vergi, 2)


@app.route("/vergi-hesapla", methods=["POST"])
def vergi_hesapla_api():
    try:
        data = request.get_json()

        yil = int(data.get("yil"))
        brut = float(data.get("brut"))
        ay = int(data.get("ay"))
        gelir_turu = data.get("gelir_turu", "ucret")
        ucret_mi = gelir_turu == "ucret"
        istisna_var = bool(data.get("istisna", False))
        onceki_dict = data.get("onceki_matrahlar", {})

        onceki_toplam = sum(float(v) for v in onceki_dict.values() if isinstance(v, (int, float, str)) and str(v).replace(".", "", 1).isdigit())

        if ucret_mi:
            if istisna_var:
                if ay == 0:
                    matrah_yillik = brut
                    istisna_ay = 12
                else:
                    matrah_yillik = onceki_toplam + brut
                    istisna_ay = ay
            else:
                # 🔧 İstisna yoksa yıllık gibi değerlendir
                matrah_yillik = onceki_toplam + brut if ay > 0 else brut
                istisna_ay = 0  # ❌ istisna olmayacak
        else:
            matrah_yillik = brut
            istisna_ay = 0

        vergi = gelir_vergisi_hesapla(yil, matrah_yillik, tarifeler, ucret=ucret_mi)

        istisna = 0.0
        tek_ay_istisna = 0.0
        if istisna_var and ucret_mi and istisna_ay > 0:
            istisna, tek_ay_istisna = asgari_ucret_istisnasi_hesapla(yil, istisna_ay, ucret=True)
            vergi -= istisna
            vergi = max(vergi, 0)

        if ay > 0 and ay < 12 and onceki_toplam > 0:
            onceki_vergi = gelir_vergisi_hesapla(yil, onceki_toplam, tarifeler, ucret=ucret_mi)
            vergi -= onceki_vergi
            vergi = max(vergi, 0)

        tam_yillik_istisna = 0.0
        if ucret_mi and istisna_var:
            tam_yillik_istisna, _ = asgari_ucret_istisnasi_hesapla(yil, 12, ucret=True)

        return jsonify({
            "vergi": round(vergi, 2),
            "istisna": round(istisna, 2),
            "istisna_ay": istisna_ay,
            "tam_istisna": round(tam_yillik_istisna, 2),
            "tek_ay_istisna": round(tek_ay_istisna, 2),
        })

    except Exception as e:
        return jsonify({"error": f"Hesaplama hatası: {str(e)}"}), 400
    
    
    
    

def asgari_ucret_istisnasi_hesapla(yil, ay_sayisi, ucret=True):
    veriler = asgari_ucretler.get(yil)
    if not veriler or "istisnalar" not in veriler:
        return 0.0, 0.0

    toplam = 0.0
    son_ay_istisnasi = 0.0
    for ay in range(1, ay_sayisi + 1):
        tutar = veriler["istisnalar"].get(ay, 0.0)
        toplam += tutar
        if ay == ay_sayisi:
            son_ay_istisnasi = tutar

    return round(toplam, 2), round(son_ay_istisnasi, 2)


@app.route("/asgari-istisna", methods=["POST"])
def asgari_istisna_api():
    try:
        data = request.get_json()
        yil = int(data.get("yil"))
        ay = int(data.get("ay_sayisi"))  # 1-12
        ucret = bool(data.get("ucret", True))

        istisna = asgari_ucret_istisnasi_hesapla(yil, ay, ucret)
        return jsonify({
            "istisna": round(istisna, 2)
        })

    except Exception as e:
        return jsonify({"error": f"Hesaplama hatası: {str(e)}"}), 400


    

# ✅ Uygulama çalıştırma kodu EN ALTA konur
if __name__ == "__main__":
    app.run(debug=True)
