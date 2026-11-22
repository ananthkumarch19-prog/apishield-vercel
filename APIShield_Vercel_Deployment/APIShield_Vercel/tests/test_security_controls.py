import json
import pytest
from application import create_app
from database.db import get_db
from database.seed import DEMO_PASSWORD
from werkzeug.security import check_password_hash
from conftest import request, login, token
from test_authorization import stored


@pytest.mark.parametrize("csrf_kind", ["missing", "invalid", "other_session"])
def test_patch_csrf_protection(app, client, csrf_kind):
    login(client, "admin@alpha.test")
    before = stored(app, 1001)
    headers = {}
    if csrf_kind == "invalid":
        headers["X-CSRFToken"] = "forged"
    elif csrf_kind == "other_session":
        headers["X-CSRFToken"] = token(app.test_client())
    response = request(client, "PATCH", "/api/invoices/1001", json={"status": "paid"}, headers=headers)
    assert response.status_code == 400
    assert response.json["reason"] == "csrf_validation_failed"
    assert stored(app, 1001) == before


def test_login_csrf_and_generic_invalid_credentials(client):
    assert request(client, "POST", "/login", json={"email": "alice@alpha.test", "password": DEMO_PASSWORD}).status_code == 400
    for email in ["alice@alpha.test", "unknown@alpha.test", "' OR 1=1 --"]:
        response = request(client, "POST", "/login", json={"email": email, "password": "wrong"}, headers={"X-CSRFToken": token(client)})
        assert response.status_code == 401
        assert response.json["error"] == "Invalid email or password."


def test_login_rotates_csrf_and_logout_requires_csrf(client):
    old = token(client)
    new = login(client, "admin@alpha.test")
    assert old != new
    assert request(client, "PATCH", "/api/invoices/1001", json={"status": "paid"}, headers={"X-CSRFToken": old}).status_code == 400
    assert request(client, "POST", "/logout").status_code == 400
    assert request(client, "POST", "/logout", headers={"X-CSRFToken": new}).status_code == 302
    assert request(client, "GET", "/api/invoices/1001").status_code == 401


@pytest.mark.parametrize("payload", [
    {}, [], None, {"company_id": 2}, {"role": "admin"}, {"user_id": 4}, {"id": 2001},
    {"amount": "NaN"}, {"amount": "Infinity"}, {"amount": "-0.01"}, {"amount": "1.001"},
    {"amount": True}, {"amount": "1000000000.01"}, {"amount": "1e999999"},
    {"customer_name": ""}, {"customer_name": "x" * 101}, {"customer_name": "bad\nname"},
    {"status": "unknown"}, {"status": ["paid"]}, {"password_hash": "forged"},
])
def test_invalid_payload_does_not_modify_record(app, client, payload):
    csrf = login(client, "admin@alpha.test")
    before = stored(app, 1001)
    response = request(client, "PATCH", "/api/invoices/1001", json=payload, headers={"X-CSRFToken": csrf})
    assert response.status_code == 400
    assert stored(app, 1001) == before


def test_malformed_json_and_body_limit(app, client):
    csrf = login(client, "admin@alpha.test")
    before = stored(app, 1001)
    response = request(client, "PATCH", "/api/invoices/1001", data='{bad json', content_type="application/json", headers={"X-CSRFToken": csrf})
    assert response.status_code == 400
    response = request(client, "PATCH", "/api/invoices/1001", data="x" * 20000, content_type="application/json", headers={"X-CSRFToken": csrf})
    assert response.status_code == 413
    assert stored(app, 1001) == before


def test_customer_text_is_escaped_in_html(client):
    csrf = login(client, "admin@alpha.test")
    name = '<script>alert("demo")</script>'
    assert request(client, "PATCH", "/api/invoices/1001", json={"customer_name": name}, headers={"X-CSRFToken": csrf}).status_code == 200
    response = request(client, "GET", "/invoices/1001")
    assert name not in response.text
    assert "&lt;script&gt;" in response.text
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]


def test_salted_password_kdf_and_foreign_keys(app):
    with app.app_context():
        db = get_db()
        hashes = [row[0] for row in db.execute("SELECT password_hash FROM users")]
        assert len(set(hashes)) == 4
        assert all(h.startswith("scrypt:32768:8:3$") for h in hashes)
        assert all(check_password_hash(h, DEMO_PASSWORD) for h in hashes)
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_audit_records_real_decisions_without_secrets(app, client):
    csrf = login(client)
    request(client, "GET", "/api/invoices/1001")
    request(client, "GET", "/api/invoices/2001")
    with app.app_context():
        events = [dict(row) for row in get_db().execute("SELECT * FROM security_events")]
    assert any(e["decision"] == "ALLOW" and e["resource_id"] == "1001" for e in events)
    denial = next(e for e in events if e["resource_id"] == "2001")
    assert denial["decision"] == "DENY" and denial["reason"] == "company_mismatch"
    assert denial["company_id"] == 1 and denial["user_id"] == 1
    text = json.dumps(events)
    assert DEMO_PASSWORD not in text and csrf not in text
    assert "password_hash" not in text and "Orchid Logistics" not in text
    page = request(client, "GET", "/security-monitoring")
    assert "company mismatch" in page.text and "#2001" in page.text


def test_cookie_security_headers_and_no_cors(client):
    response = request(client, "GET", "/auth/csrf")
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.parametrize("path", ["/lab/invoices/2001", "/api/invoices/1001", "/auth/csrf"])
def test_non_loopback_rejected_even_with_forwarded_header(client, path):
    response = request(client, "GET", path, environ_overrides={"REMOTE_ADDR": "192.0.2.25"}, headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403


def test_untrusted_host_rejected(client):
    assert client.get("/health", base_url="http://external.example").status_code == 400


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_vulnerable_routes_disabled_by_default(app, method):
    safe = create_app({"TESTING": True, "SECRET_KEY": "separate-test-key-" * 4, "DATABASE": app.config["DATABASE"],
                       "RESULTS_DIR": app.config["RESULTS_DIR"], "LAB_MODE": False})
    client = safe.test_client()
    csrf = login(client)
    response = request(client, method, "/lab/invoices/2001", json={"status": "paid"}, headers={"X-CSRFToken": csrf})
    assert response.status_code == 404


def test_vulnerable_comparison_is_real_and_still_requires_csrf(app, client):
    csrf = login(client)
    assert request(client, "GET", "/lab/invoices/2001").json["invoice"]["company_id"] == 2
    assert request(client, "GET", "/api/invoices/2001").status_code == 403
    before = stored(app, 2001)
    assert request(client, "PATCH", "/lab/invoices/2001", json={"amount": "1.00"}).status_code == 400
    assert stored(app, 2001) == before
    assert request(client, "PATCH", "/lab/invoices/2001", json={"amount": "1.00"}, headers={"X-CSRFToken": csrf}).status_code == 200
    assert stored(app, 2001)["amount"] == 100


def test_unmarked_database_lab_gate(app, client):
    login(client)
    with app.app_context():
        db = get_db()
        with db:
            db.execute("DELETE FROM metadata")
    assert request(client, "GET", "/lab/invoices/2001").status_code == 404
