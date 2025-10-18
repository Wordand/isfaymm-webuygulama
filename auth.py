from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    """
    Oturumda 'user' yoksa login sayfasına yönlendirir.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated