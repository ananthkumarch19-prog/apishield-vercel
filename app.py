"""APIShield application factory and Windows-friendly local command line."""
import argparse
import secrets
import threading
from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException, SecurityError
from config import Config
from database.db import close_db, is_demo_database
from authentication.routes import auth, login_manager
from security.audit import log_event


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(overrides or {})
    if not app.config["SECRET_KEY"]:
        secret_file = Path(app.config["SECRET_FILE"])
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with secret_file.open("x", encoding="ascii") as handle:
                handle.write(secrets.token_hex(32))
            secret_file.chmod(0o600)
        except FileExistsError:
            pass
        app.config["SECRET_KEY"] = secret_file.read_text(encoding="ascii").strip()
    if len(app.config["SECRET_KEY"]) < 32:
        raise ValueError("APISHIELD_SECRET_KEY must contain at least 32 characters.")
    Path(app.config["RESULTS_DIR"]).mkdir(parents=True, exist_ok=True)
    app.extensions["simulation_lock"] = threading.Lock()
    app.teardown_appcontext(close_db)
    login_manager.init_app(app)

    @app.before_request
    def local_and_identity_guards():
        # Never trust X-Forwarded-For/Host. There is no reverse-proxy deployment.
        if request.remote_addr != "127.0.0.1":
            abort(403, description="local_connections_only")
        if request.path.startswith("/lab/") and not app.config["LAB_MODE"]:
            abort(404)
        if request.path.startswith(("/api/", "/lab/")) and not current_user.is_authenticated:
            log_event("invoice", (request.view_args or {}).get("invoice_id"),
                      "update" if request.method == "PATCH" else "read", "DENY", "authentication_required")
            abort(401, description="authentication_required")

    # Register AFTER identity guard: unauthenticated API writes get 401, not a CSRF 400.
    CSRFProtect(app)
    app.register_blueprint(auth)
    from api.protected import api
    from web import web
    app.register_blueprint(api)
    app.register_blueprint(web)
    if app.config["LAB_MODE"]:
        from api.vulnerable_lab import lab
        app.register_blueprint(lab)

    @app.get("/health")
    def health():
        ready = is_demo_database()
        return jsonify(application="APIShield", initialized=ready, lab_mode=app.config["LAB_MODE"]), 200 if ready else 503

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        log_event("request", (request.view_args or {}).get("invoice_id"), "csrf_validation", "DENY", "csrf_validation_failed")
        return error_response(400, "csrf_validation_failed")

    def error_response(code, reason):
        if request.path.startswith(("/api/", "/lab/", "/auth/")) or request.is_json:
            return jsonify(error={401:"Authentication required", 403:"Access denied", 404:"Not found"}.get(code, "Request rejected"), reason=reason), code
        return render_template("error.html", code=code, reason=reason), code

    @app.errorhandler(HTTPException)
    def http_error(error):
        return error_response(error.code, error.description)

    @app.errorhandler(SecurityError)
    def invalid_host(_error):
        # Host validation can fail before Flask has a URL adapter. Do not render
        # a template using url_for() in this early rejection path.
        return jsonify(error="Request rejected", reason="untrusted_host"), 400

    @app.after_request
    def secure_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.template_filter("money")
    def money(paise):
        return f"{paise / 100:,.2f}"

    return app


def main():
    parser = argparse.ArgumentParser(description="APIShield: local fictional invoice security demonstration")
    parser.add_argument("command", choices=["init-db", "serve", "reset-demo"])
    parser.add_argument("--lab", action="store_true", help="Explicitly enable vulnerable local demonstration endpoints")
    parser.add_argument("--confirm-reset", action="store_true", help="Restore fictional invoices; retain audit logs")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app = create_app({"LAB_MODE": args.lab or Config.LAB_MODE})
    with app.app_context():
        if args.command == "init-db":
            from database.seed import seed_demo
            if is_demo_database():
                print("Fictional database already initialized. Existing invoices and audit history retained.")
            else:
                seed_demo()
                print("Created and seeded the fictional database. See README.md for demo accounts.")
        elif args.command == "reset-demo":
            if not app.config["LAB_MODE"] or not args.confirm_reset:
                parser.error("reset-demo requires --lab --confirm-reset")
            from database.seed import reset_invoices
            reset_invoices()
            for file in Path(app.config["RESULTS_DIR"]).glob("result-*.json"):
                file.unlink()
            print("Fictional invoices restored. Users and audit history retained.")
        else:
            if not is_demo_database():
                parser.error("Run python app.py init-db first.")
            print("LOCAL FICTIONAL LAB ENABLED" if app.config["LAB_MODE"] else "Protected mode: vulnerable endpoints disabled")
            app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
