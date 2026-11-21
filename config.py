"""Local-only defaults. No debug server, public bind, or built-in secret."""
import os
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Config:
    DATABASE = str(ROOT / "database" / "apishield.sqlite")
    SECRET_FILE = str(ROOT / "instance" / "secret.key")
    RESULTS_DIR = str(ROOT / "instance" / "results")
    LAB_MODE = os.environ.get("APISHIELD_LAB_MODE", "0") == "1"
    SIMULATOR_ENABLED = True
    SECRET_KEY = os.environ.get("APISHIELD_SECRET_KEY") or None
    SESSION_COOKIE_NAME = "apishield_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    # HTTP is deliberately restricted to loopback. HTTPS would require True.
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    WTF_CSRF_TIME_LIMIT = 3600  # Seconds, accepted by the installed Flask-WTF version.
    MAX_CONTENT_LENGTH = 16 * 1024
    TRUSTED_HOSTS = ["127.0.0.1"]
    TESTING = False
