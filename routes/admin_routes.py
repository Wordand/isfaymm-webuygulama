from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash
from services.db import get_conn
from auth import login_required
import re
import psycopg2.extras

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route("/users")
@login_required
def admin_users():
    if session.get("username", "").lower() != "admin":
        flash("Bu sayfaya erişim izniniz yok.", "danger")
        return redirect(url_for("main.home"))

    q = request.args.get("q", "").strip()
    status = request.args.get("status")
    role = request.args.get("role")

    query = "SELECT id, username, is_approved, is_suspended, role, has_kdv_access, created_at, last_login, admin_notes FROM users WHERE 1=1"
    params = []

    if q:
        query += " AND username ILIKE %s"
        params.append(f"%{q}%")

    if status in ("0", "1"):
        query += " AND is_approved = %s"
        params.append(status)

    if role in ("admin", "editor", "user"):
        query += " AND role = %s"
        params.append(role)

    query += " ORDER BY id DESC"

    try:
        with get_conn() as conn:
            # Explicitly use RealDictCursor for consistency
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute(query, tuple(params))
            rows = c.fetchall()
            users = [dict(r) for r in rows]
        
        return render_template("admin/admin_users.html", users=users)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in admin_users: {e}\n{traceback.format_exc()}")
        flash("Kullanıcı listesi yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("main.home"))

@bp.route("/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_approved = 1 WHERE id = %s", (user_id,))
        conn.commit()
    flash("Kullanıcı başarıyla onaylandı ✅", "success")
    return redirect(url_for("admin.admin_users"))

@bp.route("/reject/<int:user_id>")
@login_required
def reject_user(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        row = c.fetchone()
        # row can be dict or tuple
        username = row["username"] if isinstance(row, dict) else row[0]
        
        if username and username.lower() == "admin":
            flash("Admin hesabı silinemez ❌", "warning")
            return redirect(url_for("admin.admin_users"))

        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

    flash("Kullanıcı kaydı silindi ❌", "info")
    return redirect(url_for("admin.admin_users"))

@bp.route('/update_username/<int:user_id>', methods=['POST'])
@login_required
def update_username(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    new_username = request.form.get('new_username', '').strip()
    if not new_username:
        flash("Yeni kullanıcı adı boş olamaz.", "warning")
        return redirect(url_for('admin.admin_users'))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, user_id))
        conn.commit()

    flash("Kullanıcı adı başarıyla güncellendi ✅", "success")
    return redirect(url_for('admin.admin_users'))

@bp.route('/suspend/<int:user_id>')
@login_required
def suspend_user(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE users
            SET is_suspended = CASE WHEN is_suspended = 1 THEN 0 ELSE 1 END
            WHERE id = %s
        """, (user_id,))
        conn.commit()

    flash("Kullanıcının askıya alma durumu değiştirildi.", "info")
    return redirect(url_for('admin.admin_users'))

@bp.route('/change_role/<int:user_id>', methods=['POST'])
@login_required
def change_role(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    new_role = request.form.get('role')
    if new_role not in ['admin', 'editor', 'user']:
        flash("Geçersiz rol seçimi.", "warning")
        return redirect(url_for('admin.admin_users'))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()

    flash("Kullanıcı rolü başarıyla güncellendi.", "success")
    return redirect(url_for('admin.admin_users'))

@bp.route("/reset_password/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin_reset_password(user_id):
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.home"))

    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        user = c.fetchone()
        if not user:
            flash("Kullanıcı bulunamadı.", "warning")
            return redirect(url_for("admin.admin_users"))

    if request.method == "POST":
        new1 = request.form.get("new_password", "")
        new2 = request.form.get("new_password_confirm", "")

        if not new1 or not new2:
            flash("Lütfen yeni şifre alanlarını doldurun.", "warning")
            # user dict, jinja can access user.username
            return render_template("admin/admin_reset_password.html", user=user)

        if new1 != new2:
            flash("Yeni şifreler eşleşmiyor.", "warning")
            return render_template("admin/admin_reset_password.html", user=user)

        if len(new1) < 8 or not re.search(r"\d", new1) or not re.search(r"[A-Za-z]", new1):
            flash("Yeni şifre en az 8 karakter olmalı ve hem harf hem rakam içermelidir.", "warning")
            return render_template("admin/admin_reset_password.html", user=user)

        if user["username"].lower() == "admin":
            flash("Admin hesabını sadece admin değiştirebilir.", "danger")
            return redirect(url_for("admin.admin_users"))

        new_hash = generate_password_hash(new1)
        with get_conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))
            conn.commit()

        flash(f"{user['username']} kullanıcısının şifresi başarıyla sıfırlandı.", "success")
        return redirect(url_for("admin.admin_users"))

    return render_template("admin/admin_reset_password.html", user=user)

@bp.route("/login_logs")
@login_required
def login_logs():
    if session.get("username", "").lower() != "admin":
        flash("Bu sayfaya erişim izniniz yok.", "danger")
        return redirect(url_for("main.home"))

    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 100")
            rows = c.fetchall()
            logs = [dict(r) for r in rows]

        return render_template("admin/admin_login_logs.html", logs=logs)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in login_logs: {e}\n{traceback.format_exc()}")
        flash("Giriş logları yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for("admin.admin_users"))

@bp.route("/delete_all_logs", methods=["POST"])
@login_required
def delete_all_logs():
    if session.get("username", "").lower() != "admin":
        flash("Bu işlemi yapma yetkiniz yok.", "danger")
        return redirect(url_for("admin.login_logs"))

    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM login_logs")
        conn.commit()

    flash("Tüm log kayıtları başarıyla silindi.", "success")
    return redirect(url_for("admin.login_logs"))
