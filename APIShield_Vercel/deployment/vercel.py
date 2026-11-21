"""Configure the protected Flask app from Vercel's server environment."""
import os
import re
from urllib.parse import urlsplit

from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from application import create_app


def create_vercel_app(database_url, secret_key, hosts):
    if urlsplit(database_url).scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must be a PostgreSQL connection string.")
    if not isinstance(secret_key, str) or len(secret_key) < 32:
        raise ValueError("APISHIELD_SECRET_KEY must contain at least 32 random characters.")
    if not hosts or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)
                        or ".." in host or "." not in host for host in hosts):
        raise ValueError("Configure exact deployment hosts without schemes, paths or wildcards.")
    app = create_app({
        "PUBLIC_DEMO": True,
        "DATABASE_URL": database_url,
        "SECRET_KEY": secret_key,
        "TRUSTED_HOSTS": hosts,
        "PREFERRED_URL_SCHEME": "https",
        "DEBUG": False,
        "TESTING": False,
    })
    # Vercel provides this protocol header. Host and identity headers stay untrusted.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)
    return app


def configured_app():
    database_url = os.environ.get("DATABASE_URL", "")
    secret_key = os.environ.get("APISHIELD_SECRET_KEY", "")
    hosts = [os.environ.get(name, "") for name in
             ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL")]
    hosts.extend(os.environ.get("APISHIELD_ALLOWED_HOSTS", "").split(","))
    hosts = list(dict.fromkeys(host.strip().lower() for host in hosts if host.strip()))
    try:
        return create_vercel_app(database_url, secret_key, hosts)
    except ValueError:
        # First import can happen before the project's Storage integration is connected.
        # Keep that deployment closed until the owner sets the required configuration.
        setup_app = Flask(__name__)

        @setup_app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
        @setup_app.route("/<path:path>", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
        def setup_required(path):
            response = jsonify(application="APIShield", initialized=False,
                               reason="deployment_configuration_required",
                               message="Connect Neon Storage, set APISHIELD_SECRET_KEY and enable Vercel system environment variables, then redeploy.")
            response.headers["Cache-Control"] = "no-store"
            return response, 404 if path.startswith("lab/") else 503

        return setup_app
