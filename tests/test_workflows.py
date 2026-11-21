from database.db import get_db
from conftest import request, login
from test_authorization import stored
from simulator.engine import run_scenarios, export_results


def test_employee_pages_and_tenant_boundary(client):
    login(client)
    for path in ["/dashboard", "/invoices", "/invoices/1001", "/security-lab", "/security-monitoring"]:
        response = request(client, "GET", path)
        assert response.status_code == 200
        assert "Orchid Logistics" not in response.text
    assert request(client, "GET", "/invoices/2001").status_code == 403
    assert request(client, "GET", "/invoices/1001/edit").status_code == 403
    assert request(client, "GET", "/test-results").status_code == 403


def test_admin_html_update_uses_same_policy(app, client):
    csrf = login(client, "admin@alpha.test")
    assert request(client, "GET", "/invoices/1001/edit").status_code == 200
    assert request(client, "GET", "/invoices/2001/edit").status_code == 403
    response = request(client, "POST", "/invoices/1001/edit", data={"csrf_token": csrf, "customer_name": "Cedar Office Supplies", "amount": "43123.45", "status": "paid"})
    assert response.status_code == 302
    assert stored(app, 1001)["amount"] == 4312345
    assert stored(app, 1001)["status"] == "paid"
    before = stored(app, 2001)
    response = request(client, "POST", "/invoices/2001/edit", data={"csrf_token": csrf, "amount": "1.00"})
    assert response.status_code == 403
    assert stored(app, 2001) == before


def test_monitoring_is_scoped_to_actor_company(app, client):
    bob = app.test_client()
    login(bob, "bob@beta.test")
    request(bob, "GET", "/api/invoices/2002")
    login(client, "admin@alpha.test")
    page = request(client, "GET", "/security-monitoring")
    assert "#2002" not in page.text
    assert "Bob" not in page.text


def test_reset_requires_admin_csrf_and_restores_invoices(app, client):
    csrf = login(client)
    assert request(client, "POST", "/security-lab/reset", headers={"X-CSRFToken": csrf}).status_code == 403
    csrf = login(client, "admin@alpha.test")
    request(client, "PATCH", "/api/invoices/1001", json={"amount": "1.00"}, headers={"X-CSRFToken": csrf})
    assert request(client, "POST", "/security-lab/reset").status_code == 400
    assert stored(app, 1001)["amount"] == 100
    assert request(client, "POST", "/security-lab/reset", headers={"X-CSRFToken": csrf}).status_code == 302
    assert stored(app, 1001)["amount"] == 4250000
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM security_events WHERE reason='fictional_invoices_restored_audit_retained'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM security_events WHERE action='update'").fetchone()[0] > 0


def test_all_scenarios_over_actual_http_and_exports(tmp_path):
    result = run_scenarios()
    assert result["total"] == 15
    assert result["failed"] == 0, result
    assert all(row["passed"] for row in result["results"])
    assert len(result["audit_events"]) >= 16
    by_id = {row["test_id"]: row for row in result["results"]}
    assert by_id["C-P"]["before"] == by_id["C-P"]["after"]
    assert by_id["C-L"]["before"] != by_id["C-L"]["after"]
    assert by_id["C-P"]["before"] == by_id["C-L"]["before"]
    export_results(result, tmp_path)
    assert (tmp_path / "security_results.json").exists()
    assert "actual_status" in (tmp_path / "security_results.csv").read_text()


def test_dashboard_runs_real_simulation_and_leaves_own_data_unchanged(app, client):
    csrf = login(client, "admin@alpha.test")
    before = stored(app, 2001)
    response = request(client, "POST", "/security-lab/run", data={"group": "modification", "csrf_token": csrf})
    assert response.status_code == 302
    page = request(client, "GET", "/test-results")
    assert "2 / 2" in page.text
    assert "database_unchanged=True" in page.text
    assert stored(app, 2001) == before
    assert "disposable local http run completed" in request(client, "GET", "/security-monitoring").text


def test_run_controls_require_authorization_and_valid_group(app, client):
    csrf = login(client)
    assert request(client, "POST", "/security-lab/run", data={"group": "all", "csrf_token": csrf}).status_code == 403
    csrf = login(client, "admin@alpha.test")
    assert request(client, "POST", "/security-lab/run", data={"group": "http://external.example", "csrf_token": csrf}).status_code == 400
    assert request(client, "POST", "/security-lab/run", data={"group": "all"}).status_code == 400
    lock = app.extensions["simulation_lock"]
    with lock:
        assert request(client, "POST", "/security-lab/run", data={"group": "all", "csrf_token": csrf}).status_code == 409
