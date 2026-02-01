from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from services.db import get_conn
from extensions import limiter
from datetime import timedelta
import re
import psycopg2.extras

bp = Blueprint('auth', __name__)

def log_login_attempt(username, success, user_id=None):
    with get_conn() as conn:
        c = conn.cursor()
        ip = request.remote_addr
        agent = request.headers.get("User-Agent", "Bilinmiyor")[:255]

        c.execute(
            "INSERT INTO login_logs (user_id, username, ip_address, user_agent, success) VALUES (%s, %s, %s, %s, %s)",
            (user_id, username, ip, agent, bool(success))
        )
        conn.commit()

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        if not username or not password:
            flash("Kullanıcı adı ve şifre boş olamaz.", "warning")
            return render_template("auth/register.html")
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalı.", "warning")
            return render_template("auth/register.html")
        
        hashed_password = generate_password_hash(password)

        try:
            with get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    (username, hashed_password, 'user')
                )
                conn.commit()
            flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            # Integrity error usually
            flash("Bu kullanıcı adı zaten var. Lütfen farklı bir kullanıcı adı seçin.", "danger")
            return render_template("auth/register.html")
        
    return render_template("auth/register.html")

@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("50 per 10 minutes")
def login():
    if session.get("user_id"):
        return redirect(url_for('main.home'))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute(
                "SELECT id, password, is_approved, is_suspended, role FROM users WHERE username = %s",
                (username,)
            )
            result = c.fetchone()

        if result and check_password_hash(result["password"], password):
            user_id = result["id"]
            log_login_attempt(username, success=True, user_id=user_id)
            is_approved = result["is_approved"]
            is_suspended = result.get("is_suspended", 0)
            
            if result.get("role") == "admin" and username.lower() != "admin":
                flash("Admin rolü yalnızca sistem yöneticisine ayrılmıştır.", "danger")
                return render_template("auth/login.html")

            if is_approved == 0:
                flash("Hesabınız henüz admin tarafından onaylanmadı.", "warning")
                return render_template("auth/login.html")

            if is_suspended == 1:
                flash("Hesabınız askıya alınmıştır. Lütfen yöneticiyle iletişime geçin.", "danger")
                return render_template("auth/login.html")

            session.clear()
            session["user_id"] = user_id
            session["username"] = username
            session["logged_in"] = True

            remember = request.form.get("remember")
            if remember:
                current_app.permanent_session_lifetime = timedelta(days=30)
                session.permanent = True
            else:
                current_app.permanent_session_lifetime = timedelta(minutes=30)
                session.permanent = False

            with get_conn() as conn:
                c = conn.cursor()
                # Check nature of conn to invoke correct sql if needed, but get_conn handles it mostly via FakeCursor normalization ?
                # FakeCursor handles ? vs %s. But NOW() replacement is in FakeCursor.
                # If pg use NOW(), if sqlite CURRENT_TIMESTAMP. FakeCursor handles NOW() -> CURRENT_TIMESTAMP.
                # So we can use NOW() safely if FakeCursor wraps it.
                # Real postgres connection doesn't use FakeCursor.
                # So we should valid SQL.
                # app.py had a check: if "sqlite3" in conn.__class__.__module__
                # But get_conn returns raw pg conn or FakeConnection.
                # Let's try to be generic or use the previous logic.
                
                # app.py logic:
                if "sqlite3" in str(type(conn)): # rough check, or check module
                     c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
                else:
                     c.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))

                conn.commit()

            flash(f"Hoş geldiniz, {username}!", "success")

            if username.lower() == "admin":
                return redirect(url_for("admin.admin_users"))
            else:
                return redirect(url_for("main.home"))

        else:
            log_login_attempt(username, success=False)
            flash("Hatalı kullanıcı adı veya şifre.", "danger")

    return render_template("auth/login.html")

@bp.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for("main.home"))


from auth import login_required  # Existing decorator

@bp.route("/change_password", methods=["GET", "POST"])
@limiter.limit("5 per 5 minutes")
@login_required
def change_password():
    username = session.get("user") or session.get("username") # user vs username key consistency?
    # app.py uses session["user"] = username in some places (old app_yedek) but app.py uses session["username"] = username
    # Let's use session["username"] as standard per app.py line 379.
    
    if not username:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        current = request.form.get("current_password", "")
        new1 = request.form.get("new_password", "")
        new2 = request.form.get("new_password_confirm", "")

        if not current or not new1 or not new2:
            flash("Tüm alanları doldurun.", "warning")
            return render_template("auth/change_password.html")

        if new1 != new2:
            flash("Yeni şifreler eşleşmiyor.", "warning")
            return render_template("auth/change_password.html")

        if len(new1) < 8 or not re.search(r"\d", new1) or not re.search(r"[A-Za-z]", new1):
            flash("Yeni şifre en az 8 karakter olmalı ve hem harf hem rakam içermelidir.", "warning")
            return render_template("auth/change_password.html")

        with get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            row = c.fetchone()
            # row is dict or tuple depending on factory. get_conn uses RealDictCursor for PG.
            # FakeCursor returns dict.
            # So row["password"] is safe.
            
            if not row or not check_password_hash(row["password"], current):
                flash("Mevcut şifre hatalı.", "danger")
                return render_template("auth/change_password.html")

            new_hash = generate_password_hash(new1)
            c.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, row["id"]))
            conn.commit()

        flash("Şifreniz başarıyla değiştirildi.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/change_password.html")
