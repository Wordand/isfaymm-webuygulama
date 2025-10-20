from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or "user" not in session:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function