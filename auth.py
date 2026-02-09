from functools import wraps
from flask import session, redirect, url_for, flash, abort, request, jsonify
from services.db import get_conn



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or "user_id" not in session:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function




def role_required(
    *,
    allow_roles=None,
    require_assignment=False,
    assignment_param=None
):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            user_id = session.get("user_id")

            def forbidden():
                if request.path.startswith("/api/"):
                    return jsonify({"status": "error", "message": "Yetkisiz erişim"}), 403
                abort(403)

            # Oturum kontrolü
            if not role or not user_id:
                return forbidden()

            # Rol kontrolü
            if allow_roles and role not in allow_roles:
                return forbidden()

            # Uzman için atanmış mükellef kontrolü
            if require_assignment and role == "uzman":
                if not assignment_param:
                    return forbidden()

                mukellef_id = None

                if assignment_param in kwargs:
                    mukellef_id = kwargs.get(assignment_param)

                if not mukellef_id and request.is_json:
                    mukellef_id = request.json.get(assignment_param)

                if not mukellef_id:
                    return forbidden()

                with get_conn() as conn:
                    c = conn.cursor()
                    c.execute("""
                        SELECT 1
                        FROM kdv_user_assignments
                        WHERE user_id = %s AND mukellef_id = %s
                    """, (user_id, mukellef_id))
                    if not c.fetchone():
                        return forbidden()

            return f(*args, **kwargs)
        return wrapped
    return decorator





def kdv_access_required(f):
    """
    KDV Yönetim Paneline sadece has_kdv_access=True olan kişilerin 
    veya sistem yöneticisinin girmesini sağlar.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or "user_id" not in session:
            return redirect(url_for("auth.login"))
            
        # Hard isolation: Explicit flag check
        if not session.get("has_kdv_access") and session.get("username", "").lower() != "admin":
            flash("KDV Yönetim Paneline erişim yetkiniz bulunmamaktadır. Bu alan kısıtlıdır.", "danger")
            return redirect(url_for("main.home"))
            
        # PIN Verification check
        if not session.get("kdv_portal_pin_verified"):
            return redirect(url_for("kdv.verify_pin"))
            
        return f(*args, **kwargs)
    return decorated_function

def api_kdv_access_required(f):
    """
    API uçları için KDV erişim kontrolü. 
    Yönlendirme yapmak yerine JSON hatası döner.
    """
    from functools import wraps
    from flask import session, jsonify
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or "user_id" not in session:
            return jsonify({"status": "error", "message": "Oturum kapalı. Lütfen tekrar giriş yapın."}), 401
            
        if not session.get("has_kdv_access") and session.get("username", "").lower() != "admin":
            return jsonify({"status": "error", "message": "KDV Portalı yetkiniz bulunmamaktadır."}), 403
            
        if not session.get("kdv_portal_pin_verified"):
            return jsonify({"status": "error", "message": "KDV Portalı PIN doğrulaması yapılmamış."}), 403
            
        return f(*args, **kwargs)
    return decorated_function