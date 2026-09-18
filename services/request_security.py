from flask import jsonify, request
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import BadRequest


def init_request_security(app):
    # Limit this rollout to the cookie-authenticated admin and KDV portals.
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False
    csrf = CSRFProtect(app)
    protected_blueprints = {"admin", "kdv"}

    @app.before_request
    def protect_portal_changes():
        if request.blueprint in protected_blueprints and request.method in {
            "POST", "PUT", "PATCH", "DELETE"
        }:
            csrf.protect()

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = "İstek doğrulanamadı. Sayfayı yenileyip tekrar deneyin."
        if request.path.startswith("/api/"):
            return jsonify(status="error", message=message), 400
        return BadRequest(description=message).get_response()

    @app.after_request
    def disable_portal_caching(response):
        if request.blueprint in protected_blueprints:
            response.headers["Cache-Control"] = "no-store"
        return response
