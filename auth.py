from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or "user_id" not in session:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("logged_in") or "user_id" not in session:
                flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
                return redirect(url_for("auth.login"))
            
            user_role = session.get("role")
            if user_role not in roles and "admin" not in roles:
                if user_role != "admin":
                    flash("Bu işlemi yapmak için yetkiniz bulunmamaktadır.", "danger")
                    return redirect(url_for("main.home"))
                    
            return f(*args, **kwargs)
        return decorated_function
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