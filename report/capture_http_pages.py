"""Optional real-HTTP evidence capture. This does NOT capture a browser.

Run the dashboard with --lab first, then run this from the project directory:
    python report/capture_http_pages.py
Uses only fictional demo data. Restores fixtures before completing.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:5000"
OUT = ROOT / "screenshots" / "rendered_http_pages"
OUT.mkdir(parents=True, exist_ok=True)
checks = []
captures = []
client = requests.Session()
client.trust_env = False


def csrf():
    response = client.get(BASE + "/auth/csrf", timeout=10)
    response.raise_for_status()
    return response.json()["csrf_token"]


def login(email):
    response = client.post(BASE + "/login", json={"email": email, "password": "Demo@2026!"},
                           headers={"X-CSRFToken": csrf()}, timeout=10, allow_redirects=False)
    assert response.status_code == 200
    return csrf()


def capture(name, path, expected=200):
    response = client.get(BASE + path, timeout=10, allow_redirects=False)
    assert response.status_code == expected, (path, response.status_code)
    html = response.text
    # No cookies or tokens are written to evidence files.
    html = re.sub(r'(<input[^>]+name="csrf_token"[^>]+value=")[^"]*(")', r'\1REDACTED\2', html)
    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    html = re.sub(r'<link rel="stylesheet"[^>]+>', lambda _m: "<style>" + css + "</style>", html)
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S)
    (OUT / f"{name}.html").write_text(html, encoding="utf-8")
    captures.append({"file": f"{name}.html", "path": path, "status": response.status_code,
                     "kind": "Actual server HTML, CSRF redacted; not a browser screenshot"})
    return response


try:
    capture("01_login", "/login")
    login("alice@alpha.test")
    overview = capture("02_alice_overview", "/dashboard")
    assert "Alpha Traders" in overview.text and "Orchid Logistics" not in overview.text
    checks.append({"name": "Live login and dashboard tenant scope", "passed": True})
    listing = capture("03_company_invoices", "/invoices")
    assert "INV-1001" in listing.text and "INV-2001" not in listing.text
    checks.append({"name": "Company-scoped HTML listing", "passed": True})
    capture("04_invoice_details", "/invoices/1001")
    denied = capture("05_cross_company_denied", "/invoices/2001", 403)
    assert "Orchid Logistics" not in denied.text
    checks.append({"name": "Direct HTML cross-company denial", "passed": True, "http": 403})
    protected = client.get(BASE + "/api/invoices/2001", timeout=10)
    vulnerable = client.get(BASE + "/lab/invoices/2001", timeout=10)
    assert protected.status_code == 403 and vulnerable.status_code == 200
    assert "invoice" not in protected.json()
    checks.append({"name": "Same Alice live session and target", "passed": True, "protected": protected.json(),
                   "lab": vulnerable.json(), "statuses": [403, 200]})
    admin_csrf = login("admin@alpha.test")
    capture("06_authorized_management", "/invoices/1001/edit")
    updated = client.post(BASE + "/invoices/1001/edit", data={"csrf_token": admin_csrf, "customer_name": "Cedar Office Supplies",
                          "amount": "43123.45", "status": "paid"}, timeout=10, allow_redirects=False)
    assert updated.status_code == 302
    persisted = client.get(BASE + "/api/invoices/1001", timeout=10).json()["invoice"]
    assert persisted["amount"] == "43123.45" and persisted["status"] == "paid"
    capture("07_saved_update", "/invoices/1001")
    checks.append({"name": "HTML administrator update persisted", "passed": True, "amount": persisted["amount"]})
    capture("08_security_lab", "/security-lab")
    run = client.post(BASE + "/security-lab/run", data={"csrf_token": admin_csrf, "group": "all"}, timeout=40, allow_redirects=False)
    assert run.status_code == 302
    page = capture("09_test_results", "/test-results")
    assert "15 / 15" in page.text and "database_unchanged=True" in page.text
    assert client.get(BASE + "/api/invoices/1001", timeout=10).json()["invoice"]["amount"] == "43123.45"
    checks.append({"name": "Dashboard ran actual HTTP comparisons without changing dashboard invoice", "passed": True, "scenario_results": 15})
    audit = capture("10_security_monitoring", "/security-monitoring")
    assert "company mismatch" in audit.text and "disposable local http run completed" in audit.text
    checks.append({"name": "Stored real decisions displayed in monitoring", "passed": True})
    reset = client.post(BASE + "/security-lab/reset", data={"csrf_token": admin_csrf}, timeout=10, allow_redirects=False)
    assert reset.status_code == 302
    restored = client.get(BASE + "/api/invoices/1001", timeout=10).json()["invoice"]
    assert restored["amount"] == "42500.00" and restored["status"] == "pending"
    checks.append({"name": "Live reset restored the fictional invoice", "passed": True})
    logout = client.post(BASE + "/logout", data={"csrf_token": admin_csrf}, timeout=10, allow_redirects=False)
    assert logout.status_code == 302
    assert client.get(BASE + "/api/invoices/1001", timeout=10).status_code == 401
    checks.append({"name": "Live logout revoked this client session", "passed": True})
finally:
    client.close()
    output = {"timestamp": datetime.now(timezone.utc).isoformat(), "transport": "Real HTTP using Requests, not a browser",
              "passed": len(checks), "checks": checks, "captures": captures}
    (ROOT / "report" / "evidence" / "live_workflow.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
print(f"{len(checks)} live workflow checks passed. Captured {len(captures)} actual HTTP HTML pages.")
