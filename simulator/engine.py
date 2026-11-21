"""Run actual HTTP requests against a disposable copy of the fictional app.

No destination URL is accepted from users. There is no external network target.
The web server, database, Requests sessions, and port are owned by this run.
"""
import csv
import json
import platform
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
import requests
from werkzeug.serving import make_server, WSGIRequestHandler
from database.db import connect
from database.seed import seed_demo, DEMO_PASSWORD

GROUPS = {"normal", "bola", "modification", "unauthenticated", "administrator", "all"}


class QuietHandler(WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        pass


def run_scenarios(group="all"):
    if group not in GROUPS:
        raise ValueError("Unknown scenario group")
    from app import create_app
    with tempfile.TemporaryDirectory(prefix="apishield-lab-") as directory:
        root = Path(directory)
        app = create_app({"DATABASE": str(root / "demo.sqlite"), "SECRET_KEY": secrets.token_hex(32),
                          "RESULTS_DIR": str(root / "results"), "LAB_MODE": True,
                          "SIMULATOR_ENABLED": False, "TESTING": False})
        with app.app_context():
            seed_demo()
        server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        clients = []
        started = datetime.now(timezone.utc).isoformat()
        base = f"http://127.0.0.1:{server.server_port}"
        db = connect(app.config["DATABASE"])
        rows = []
        try:
            def new_client(email=None):
                client = requests.Session()
                client.trust_env = False  # Ignore HTTP_PROXY and netrc for local-only runs.
                clients.append(client)
                if email:
                    token = client.get(base + "/auth/csrf", timeout=10, allow_redirects=False).json()["csrf_token"]
                    response = client.post(base + "/login", json={"email": email, "password": DEMO_PASSWORD},
                                           headers={"X-CSRFToken": token}, timeout=10, allow_redirects=False)
                    if response.status_code != 200:
                        raise RuntimeError(f"Simulator login failed: HTTP {response.status_code}")
                    # Login rotates session state, so obtain a fresh token.
                    token = client.get(base + "/auth/csrf", timeout=10, allow_redirects=False).json()["csrf_token"]
                    client.headers["X-CSRFToken"] = token
                return client

            alice = new_client("alice@alpha.test")
            admin = new_client("admin@alpha.test")
            anon = new_client()

            def snapshot(invoice_id):
                row = db.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
                return dict(row) if row else None

            def restore(before):
                with db:
                    db.execute("UPDATE invoices SET customer_name=?, amount=?, status=? WHERE id=?",
                               (before["customer_name"], before["amount"], before["status"], before["id"]))

            def perform(test_id, scenario, client, actor, method, path, expected, behavior,
                        *, data=None, check=None, invoice_id=None, expect_change=None, headers=None):
                before = snapshot(invoice_id) if invoice_id else None
                response = client.request(method, base + path, json=data, headers=headers, timeout=10, allow_redirects=False)
                body = response.json()
                after = snapshot(invoice_id) if invoice_id else None
                checks = {"http_status_matches": response.status_code == expected}
                if check:
                    checks.update(check(body))
                if expect_change is not None:
                    checks["database_changed" if expect_change else "database_unchanged"] = (before != after) if expect_change else before == after
                result = {"test_id": test_id, "scenario": scenario, "actor": actor,
                          "method": method, "resource": path, "expected_status": expected,
                          "actual_status": response.status_code, "expected_behavior": behavior,
                          "observed_behavior": "; ".join(f"{key}={value}" for key, value in checks.items()),
                          "reason": body.get("reason", ""), "checks": checks, "passed": all(checks.values()),
                          "response": body}
                if before is not None:
                    result["before"] = before
                    result["after"] = after
                rows.append(result)
                return before

            def confidential_absent(body):
                raw = json.dumps(body)
                return {"no_confidential_invoice_fields": not any(key in body for key in ("invoice", "amount", "customer_name", "invoice_number", "company_id")),
                        "no_target_values": "Orchid Logistics" not in raw and "INV-2001" not in raw and "96000" not in raw}

            if group in {"normal", "all"}:
                perform("A", "Normal authorized access", alice, "Alice / Alpha employee", "GET", "/api/invoices/1001", 200,
                        "Return Alpha's invoice to Alice", check=lambda b: {"correct_company": b.get("invoice", {}).get("company_id") == 1})
            if group in {"bola", "all"}:
                perform("B-L", "BOLA read through vulnerable lab", alice, "Alice / Alpha employee", "GET", "/lab/invoices/2001", 200,
                        "Demonstrate unauthorized Beta data exposure", check=lambda b: {"beta_data_exposed": b.get("invoice", {}).get("customer_name") == "Orchid Logistics"})
                perform("B-P", "Same BOLA read through protected API", alice, "Alice / Alpha employee", "GET", "/api/invoices/2001", 403,
                        "Deny without returning Beta invoice data", check=confidential_absent)
            if group in {"modification", "all"}:
                payload = {"amount": "1.00"}
                perform("C-P", "Cross-company modification blocked", alice, "Alice / Alpha employee", "PATCH", "/api/invoices/2001", 403,
                        "Deny and leave every invoice field unchanged", data=payload, check=confidential_absent, invoice_id=2001, expect_change=False)
                before = perform("C-L", "Same modification through vulnerable lab", alice, "Alice / Alpha employee", "PATCH", "/lab/invoices/2001", 200,
                                 "Demonstrate unauthorized update in disposable DB", data=payload,
                                 check=lambda b: {"unauthorized_amount_applied": b.get("invoice", {}).get("amount") == "1.00"}, invoice_id=2001, expect_change=True)
                restore(before)
            if group in {"unauthenticated", "all"}:
                perform("D", "Unauthenticated request", anon, "No authenticated session", "GET", "/api/invoices/1001", 401,
                        "Reject before returning an invoice", check=confidential_absent)
            if group in {"administrator", "all"}:
                before = perform("E", "Authorized company administrator update", admin, "Alpha Admin / Alpha administrator", "PATCH", "/api/invoices/1001", 200,
                                 "Update own-company amount to INR 45,250.00", data={"amount": "45250.00"}, invoice_id=1001, expect_change=True,
                                 check=lambda b: {"requested_amount_applied": b.get("invoice", {}).get("amount") == "45250.00"})
                restore(before)
                perform("F", "Cross-company administrator read", admin, "Alpha Admin / Alpha administrator", "GET", "/api/invoices/2001", 403,
                        "Company admin receives no global privilege", check=confidential_absent)
                perform("F-P", "Cross-company administrator update", admin, "Alpha Admin / Alpha administrator", "PATCH", "/api/invoices/2001", 403,
                        "Deny and preserve the Beta record", data={"status": "paid"}, invoice_id=2001, expect_change=False, check=confidential_absent)
            if group == "all":
                perform("G", "Nonexistent invoice", alice, "Alice / Alpha employee", "GET", "/api/invoices/999999", 404,
                        "Return not found without data", check=confidential_absent)
                perform("H", "Forged company and role claims", alice, "Alice / Alpha employee", "GET", "/api/invoices/2001?company_id=2&user_id=4&role=admin", 403,
                        "Use session identity and database permissions", headers={"X-Company-ID": "2", "X-User-ID": "4", "X-Role": "admin"}, check=confidential_absent)
                perform("H-P", "Forged ownership in PATCH body", alice, "Alice / Alpha employee", "PATCH", "/api/invoices/2001", 403,
                        "Reject before submitted identity can change permissions", data={"amount": "1.00", "company_id": 2, "user_id": 4, "role": "admin"},
                        invoice_id=2001, expect_change=False, check=confidential_absent)
                perform("I", "Employee cannot update own invoice", alice, "Alice / Alpha employee", "PATCH", "/api/invoices/1001", 403,
                        "Read permission does not imply update permission", data={"status": "paid"}, invoice_id=1001, expect_change=False)
                perform("J", "Missing CSRF token on authorized PATCH", admin, "Alpha Admin / Alpha administrator", "PATCH", "/api/invoices/1001", 400,
                        "Reject state change without a valid CSRF token", data={"status": "paid"}, headers={"X-CSRFToken": None}, invoice_id=1001, expect_change=False)
                perform("K", "Mass assignment rejected", admin, "Alpha Admin / Alpha administrator", "PATCH", "/api/invoices/1001", 400,
                        "Refuse attempts to reassign invoice company", data={"company_id": 2, "status": "paid"}, invoice_id=1001, expect_change=False)

            events = [dict(row) for row in db.execute("SELECT * FROM security_events ORDER BY id")]
            return {"application": "APIShield", "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
                    "group": group, "transport": "real HTTP via Python Requests on 127.0.0.1",
                    "environment": {"python": platform.python_version(), "platform": platform.platform()},
                    "scope": "Disposable fictional database; dashboard invoices were not modified",
                    "total": len(rows), "passed": sum(row["passed"] for row in rows),
                    "failed": sum(not row["passed"] for row in rows), "results": rows, "audit_events": events}
        finally:
            for client in clients:
                client.close()
            db.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def export_results(result, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "security_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    fields = ["test_id", "scenario", "actor", "method", "resource", "expected_status", "actual_status", "expected_behavior", "observed_behavior", "passed"]
    with (output / "security_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["results"])
