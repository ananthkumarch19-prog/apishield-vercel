"""Public profile integration tests against a real, temporary PostgreSQL server."""
import importlib.util
import json
import os
import socket
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg import sql
import pytest

from database.db import get_db
from deployment.vercel import create_vercel_app, configured_app

BASE = "https://apishield-test.vercel.app"
HOST = "apishield-test.vercel.app"
SECRET = "test-only-signing-secret-" * 3


@pytest.fixture(scope="session")
def postgres_server(tmp_path_factory):
    package = importlib.util.find_spec("pgserver")
    if package is None:
        pytest.fail("Install requirements-dev.txt to run real PostgreSQL tests.")
    binaries = Path(package.origin).parent / "pginstall" / "bin"
    suffix = ".exe" if os.name == "nt" else ""
    initdb = binaries / f"initdb{suffix}"
    pg_ctl = binaries / f"pg_ctl{suffix}"
    root = tmp_path_factory.mktemp("postgres")
    data = root / "data"
    subprocess.run([str(initdb), "-D", str(data), "-A", "trust", "-U", "apishield",
                    "--no-locale", "--encoding=UTF8"], check=True, capture_output=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    subprocess.run([str(pg_ctl), "-D", str(data), "-l", str(root / "postgres.log"),
                    "-o", f"-h 127.0.0.1 -p {port} -k '' -F", "-w", "start"],
                   check=True, capture_output=True)
    try:
        yield f"postgresql://apishield@127.0.0.1:{port}/postgres"
    finally:
        subprocess.run([str(pg_ctl), "-D", str(data), "-m", "fast", "-w", "stop"],
                       check=True, capture_output=True)


@pytest.fixture
def database_url(postgres_server):
    name = "test_" + uuid.uuid4().hex
    with psycopg.connect(postgres_server, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    yield postgres_server.rsplit("/", 1)[0] + "/" + name
    with psycopg.connect(postgres_server, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def public_app(database_url):
    return create_vercel_app(database_url, SECRET, [HOST])


def call(client, method, path, **kwargs):
    return client.open(path, method=method, base_url=BASE,
                       environ_overrides={"REMOTE_ADDR": "203.0.113.10"}, **kwargs)


def login(client, email="alice@alpha.test"):
    token = call(client, "GET", "/auth/csrf").json["csrf_token"]
    response = call(client, "POST", "/login", json={"email": email, "password": "Demo@2026!"},
                    headers={"X-CSRFToken": token, "Referer": BASE + "/login"})
    assert response.status_code == 200
    return call(client, "GET", "/auth/csrf").json["csrf_token"]


def test_first_request_initializes_postgres_and_health(public_app):
    response = call(public_app.test_client(), "GET", "/health")
    assert response.status_code == 200
    assert response.json["initialized"] is True
    assert response.json["lab_mode"] is False
    with public_app.app_context():
        assert get_db().execute("SELECT COUNT(*) AS count FROM companies").fetchone()["count"] == 2
        assert get_db().execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 4
        assert get_db().execute("SELECT COUNT(*) AS count FROM invoices").fetchone()["count"] == 8


@pytest.mark.parametrize("email,own,other", [
    ("alice@alpha.test", 1001, 2001), ("admin@alpha.test", 1001, 2001),
    ("bob@beta.test", 2001, 1001), ("admin@beta.test", 2001, 1001),
])
def test_postgres_read_matrix(public_app, email, own, other):
    client = public_app.test_client()
    login(client, email)
    assert call(client, "GET", f"/api/invoices/{own}").status_code == 200
    denied = call(client, "GET", f"/api/invoices/{other}")
    assert denied.status_code == 403
    assert "invoice" not in denied.json
    assert call(client, "GET", "/dashboard").status_code == 200
    listing = call(client, "GET", "/api/invoices").json["invoices"]
    assert len(listing) == 4
    assert all(row["company_id"] == (1 if own == 1001 else 2) for row in listing)


@pytest.mark.parametrize("email,target,expected", [
    ("alice@alpha.test", 1001, 403), ("alice@alpha.test", 2001, 403),
    ("admin@alpha.test", 1001, 200), ("admin@alpha.test", 2001, 403),
    ("bob@beta.test", 2001, 403), ("admin@beta.test", 2001, 200),
])
def test_postgres_update_matrix_and_database_state(public_app, email, target, expected):
    client = public_app.test_client()
    token = login(client, email)
    with public_app.app_context():
        before = dict(get_db().execute("SELECT * FROM invoices WHERE id=?", (target,)).fetchone())
    response = call(client, "PATCH", f"/api/invoices/{target}", json={"amount": "45250.00"},
                    headers={"X-CSRFToken": token, "Referer": BASE + "/invoices"})
    assert response.status_code == expected
    with public_app.app_context():
        after = dict(get_db().execute("SELECT * FROM invoices WHERE id=?", (target,)).fetchone())
    if expected == 403:
        assert before == after
    else:
        assert after["amount"] == 4525000
        assert response.json["invoice"]["amount"] == "45250.00"


def test_postgres_csrf_forged_identity_missing_resource(public_app):
    client = public_app.test_client()
    assert call(client, "GET", "/api/invoices/1001").status_code == 401
    token = login(client)
    assert call(client, "GET", "/api/invoices/999999").status_code == 404
    response = call(client, "GET", "/api/invoices/2001?company_id=2&role=admin")
    assert response.status_code == 403
    assert "Orchid Logistics" not in response.get_data(as_text=True)
    token = login(client, "admin@alpha.test")
    assert call(client, "PATCH", "/api/invoices/1001", json={"amount": "1.00"}).status_code == 400
    response = call(client, "PATCH", "/api/invoices/1001", json={"company_id": 2},
                    headers={"X-CSRFToken": token, "Referer": BASE + "/invoices"})
    assert response.status_code == 400
    with public_app.app_context():
        assert get_db().execute("SELECT amount FROM invoices WHERE id=1001").fetchone()["amount"] == 4250000


def test_public_lab_unavailable_even_with_environment_flag(public_app, monkeypatch):
    monkeypatch.setenv("APISHIELD_LAB_MODE", "1")
    from config import Config
    monkeypatch.setattr(Config, "LAB_MODE", True)
    assert public_app.config["LAB_MODE"] is False
    client = public_app.test_client()
    token = login(client, "admin@alpha.test")
    assert call(client, "GET", "/lab/invoices/2001").status_code == 404
    for path in ["/security-lab/run", "/security-lab/reset"]:
        assert call(client, "POST", path, data={"csrf_token": token},
                    headers={"Referer": BASE + "/security-lab"}).status_code == 404


def test_public_headers_exact_host_and_forwarded_scheme(public_app):
    client = public_app.test_client()
    response = call(client, "GET", "/auth/csrf")
    cookie = response.headers["Set-Cookie"]
    assert all(flag in cookie for flag in ["Secure", "HttpOnly", "SameSite=Strict"])
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert client.get("/login", base_url="http://" + HOST).status_code == 308
    assert client.get("/login", base_url="http://" + HOST,
                      headers={"X-Forwarded-Proto": "https"}).status_code == 200
    assert client.get("/login", base_url="https://evil.test",
                      headers={"X-Forwarded-Host": HOST}).status_code == 400


def test_postgres_persistence_and_session_across_app_instances(public_app, database_url):
    client = public_app.test_client()
    token = login(client, "admin@alpha.test")
    response = call(client, "PATCH", "/api/invoices/1001", json={"amount": "54321.00"},
                    headers={"X-CSRFToken": token, "Referer": BASE + "/invoices"})
    assert response.status_code == 200
    new_app = create_vercel_app(database_url, SECRET, [HOST])
    new_client = new_app.test_client()
    new_client.set_cookie("apishield_session", client.get_cookie("apishield_session", domain=HOST).value, domain=HOST)
    response = call(new_client, "GET", "/api/invoices/1001")
    assert response.status_code == 200
    assert response.json["invoice"]["amount"] == "54321.00"
    with new_app.app_context():
        assert get_db().execute("SELECT COUNT(*) AS count FROM invoices").fetchone()["count"] == 8


def test_concurrent_first_requests_do_not_duplicate_or_reset_data(database_url):
    apps = [create_vercel_app(database_url, SECRET, [HOST]) for _ in range(3)]

    def health(app):
        return call(app.test_client(), "GET", "/health").status_code

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(health, apps)) == [200, 200, 200]
    with apps[0].app_context():
        assert get_db().execute("SELECT COUNT(*) AS count FROM invoices").fetchone()["count"] == 8


def test_audit_insert_failure_rolls_back_authorized_update(public_app):
    client = public_app.test_client()
    token = login(client, "admin@alpha.test")
    with public_app.app_context():
        db = get_db()
        db.connection.execute("""
            CREATE FUNCTION reject_update_audit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.action = 'update' AND NEW.decision = 'ALLOW' THEN
                    RAISE EXCEPTION 'simulated audit failure';
                END IF;
                RETURN NEW;
            END $$;
            CREATE TRIGGER reject_update_audit BEFORE INSERT ON security_events
            FOR EACH ROW EXECUTE FUNCTION reject_update_audit();
        """, prepare=False)
    response = call(client, "PATCH", "/api/invoices/1001", json={"amount": "1.00"},
                    headers={"X-CSRFToken": token, "Referer": BASE + "/invoices"})
    assert response.status_code == 503
    assert "simulated audit failure" not in response.get_data(as_text=True)
    with public_app.app_context():
        assert get_db().execute("SELECT amount FROM invoices WHERE id=1001").fetchone()["amount"] == 4250000


def test_postgres_monitoring_uses_real_company_scoped_events(public_app):
    client = public_app.test_client()
    login(client, "bob@beta.test")
    call(client, "GET", "/api/invoices/2001")
    token = login(client, "alice@alpha.test")
    call(client, "GET", "/api/invoices/1001")
    page = call(client, "GET", "/security-monitoring").get_data(as_text=True)
    assert "PostgreSQL" in page
    assert "same company and permitted role" in page
    assert "Bob" not in page


def test_public_profile_does_not_write_to_source_files(public_app, monkeypatch):
    def forbid_mkdir(*_args, **_kwargs):
        raise AssertionError("Unexpected runtime filesystem write")
    monkeypatch.setattr(Path, "mkdir", forbid_mkdir)
    create_vercel_app(public_app.config["DATABASE_URL"], SECRET, [HOST])


@pytest.mark.parametrize("hosts", [[], ["*"], ["https://demo.vercel.app"], ["demo.vercel.app/"], ["a..vercel.app"]])
def test_vercel_host_validation(database_url, hosts):
    with pytest.raises(ValueError):
        create_vercel_app(database_url, SECRET, hosts)


def test_configured_entrypoint_and_missing_configuration(database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APISHIELD_SECRET_KEY", SECRET)
    monkeypatch.setenv("VERCEL_URL", HOST)
    app = configured_app()
    assert call(app.test_client(), "GET", "/health").status_code == 200
    monkeypatch.delenv("DATABASE_URL")
    missing = configured_app().test_client()
    response = missing.get("/health")
    assert response.status_code == 503
    assert response.json["initialized"] is False
    assert SECRET not in response.get_data(as_text=True)


def test_cdn_assets_match_templates(public_app):
    root = Path(__file__).resolve().parents[1]
    assert (root / "public/static/style.css").is_file()
    assert (root / "public/static/app.js").is_file()
    assert call(public_app.test_client(), "GET", "/static/style.css").status_code == 200
