import pytest
from database.db import get_db
from security.authorization import policy
from conftest import request, login


def stored(app, invoice_id):
    with app.app_context():
        return dict(get_db().execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())


def assert_no_invoice(response):
    assert "invoice" not in response.json
    assert set(response.json) == {"error", "reason"}
    assert "Orchid Logistics" not in response.text
    assert "INV-2001" not in response.text


# Explicit expected business permissions; cover both companies and both roles.
@pytest.mark.parametrize("email,target,read_status,write_status", [
    ("alice@alpha.test", 1001, 200, 403), ("alice@alpha.test", 2001, 403, 403),
    ("admin@alpha.test", 1001, 200, 200), ("admin@alpha.test", 2001, 403, 403),
    ("bob@beta.test", 1001, 403, 403), ("bob@beta.test", 2001, 200, 403),
    ("admin@beta.test", 1001, 403, 403), ("admin@beta.test", 2001, 200, 200),
])
@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_full_role_and_tenant_matrix(app, client, email, target, read_status, write_status, method):
    csrf = login(client, email)
    before = stored(app, target)
    response = request(client, method, f"/api/invoices/{target}",
                       json={"amount": "123.45"} if method == "PATCH" else None,
                       headers={"X-CSRFToken": csrf})
    assert response.status_code == (read_status if method == "GET" else write_status)
    after = stored(app, target)
    if response.status_code == 403:
        assert_no_invoice(response)
        assert before == after
    elif method == "PATCH":
        assert after["amount"] == 12345
        assert after["company_id"] == before["company_id"]
        assert response.json["invoice"]["amount"] == "123.45"
    else:
        assert response.json["invoice"]["id"] == target


@pytest.mark.parametrize("email,company", [("alice@alpha.test", 1), ("admin@alpha.test", 1), ("bob@beta.test", 2), ("admin@beta.test", 2)])
def test_list_scope_ignores_client_company(client, email, company):
    login(client, email)
    response = request(client, "GET", "/api/invoices?company_id=999&role=admin")
    assert response.status_code == 200
    assert len(response.json["invoices"]) == 4
    assert {row["company_id"] for row in response.json["invoices"]} == {company}


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_forged_identity_claims_cannot_escalate(app, client, method):
    csrf = login(client)
    before = stored(app, 2001)
    response = request(client, method, "/api/invoices/2001?company_id=2&user_id=4&role=admin",
                       json={"company_id": 2, "user_id": 4, "role": "admin", "amount": "1.00"},
                       headers={"X-CSRFToken": csrf, "X-Company-ID": "2", "X-User-ID": "4", "X-Role": "admin"})
    assert response.status_code == 403
    assert response.json["reason"] == "company_mismatch"
    assert_no_invoice(response)
    assert stored(app, 2001) == before


@pytest.mark.parametrize("target", [999999, 9223372036854775808, 10**80])
def test_nonexistent_and_out_of_range_ids(client, target):
    login(client)
    response = request(client, "GET", f"/api/invoices/{target}")
    assert response.status_code == 404
    assert_no_invoice(response)


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_unauthenticated_status_precedes_csrf(client, method):
    response = request(client, method, "/api/invoices/1001", json={"amount": "0.00"})
    assert response.status_code == 401
    assert_no_invoice(response)


def test_unknown_operation_and_unknown_role_default_deny():
    class Identity:
        is_authenticated = True
        company_id = 1
        role = "admin"
    assert policy(Identity(), 1, "delete")[0] is False
    Identity.role = "superadmin"
    assert policy(Identity(), 1, "read")[0] is False


def test_permissions_reloaded_from_database(app, client):
    csrf = login(client, "admin@alpha.test")
    with app.app_context():
        db = get_db()
        with db:
            db.execute("UPDATE users SET role='employee' WHERE id=2")
    response = request(client, "PATCH", "/api/invoices/1001", json={"status": "paid"}, headers={"X-CSRFToken": csrf})
    assert response.status_code == 403
    assert response.json["reason"] == "role_not_permitted"


def test_signed_session_tampering_rejected(client):
    login(client)
    client.set_cookie("apishield_session", "forged.admin.company2", domain="127.0.0.1")
    assert request(client, "GET", "/api/invoices/2001").status_code == 401
