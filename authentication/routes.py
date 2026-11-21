from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash
from database.db import get_db
from security.audit import log_event

auth = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.company_id = row["company_id"]
        self.name = row["name"]
        self.email = row["email"]
        self.role = row["role"]
        self.company_name = row["company_name"]


@login_manager.user_loader
def load_user(user_id):
    # Re-read company and role on EVERY request. Do not store permissions in cookies.
    if not str(user_id).isdigit() or len(str(user_id)) > 18:
        return None
    row = get_db().execute(
        "SELECT u.*, c.name AS company_name FROM users u JOIN companies c ON c.id=u.company_id WHERE u.id=?",
        (int(user_id),),
    ).fetchone()
    return User(row) if row else None


@auth.get("/auth/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(data, dict) and request.is_json:
        abort(400, description="A JSON object is required.")
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str) or len(email) > 200 or len(password) > 200:
        abort(400, description="Invalid login input.")
    row = get_db().execute(
        "SELECT u.*, c.name AS company_name FROM users u JOIN companies c ON c.id=u.company_id WHERE u.email=?",
        (email.strip().lower(),),
    ).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        log_event("session", None, "login", "DENY", "invalid_credentials", anonymous=True)
        if request.is_json:
            return jsonify(error="Invalid email or password.", reason="invalid_credentials"), 401
        return render_template("login.html", error="Invalid email or password."), 401
    session.clear()  # Remove the previous identity and pre-login CSRF state.
    login_user(User(row), remember=False, fresh=True)
    session.permanent = True
    log_event("session", None, "login", "ALLOW", "credentials_verified")
    if request.is_json:
        return jsonify(user={"name": current_user.name, "role": current_user.role, "company": current_user.company_name})
    return redirect(url_for("web.dashboard"))


@auth.post("/logout")
@login_required
def logout():
    log_event("session", None, "logout", "ALLOW", "session_ended")
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
