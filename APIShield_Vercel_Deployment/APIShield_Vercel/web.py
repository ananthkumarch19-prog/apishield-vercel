"""Server-rendered invoice UI and local demonstration controls."""
import json
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from database.db import get_db, is_demo_database
from database.seed import reset_invoices
from security.authorization import authorize_invoice, company_invoices
from security.audit import log_event
from security.invoices import update_invoice

web = Blueprint("web", __name__)


def events_for_actor(limit=100):
    query = ("SELECT e.*, u.name AS user_name FROM security_events e LEFT JOIN users u ON u.id=e.user_id "
             "WHERE e.company_id=?")
    args = [current_user.company_id]
    if current_user.role != "admin":
        query += " AND e.user_id=?"
        args.append(current_user.id)
    return get_db().execute(query + " ORDER BY e.id DESC LIMIT ?", (*args, limit)).fetchall()


def result_path():
    return Path(current_app.config["RESULTS_DIR"]) / f"result-{current_user.id}.json"


def saved_result():
    path = result_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def require_operator():
    if not current_app.config["LAB_MODE"] or not current_app.config["SIMULATOR_ENABLED"] or not is_demo_database():
        abort(404, description="Local demonstration controls are disabled.")
    if current_user.role != "admin":
        log_event("lab_control", None, "operate", "DENY", "company_admin_required")
        abort(403, description="Company administrators may operate the local demonstration controls.")


@web.get("/")
@web.get("/dashboard")
@login_required
def dashboard():
    invoices = company_invoices()
    events = events_for_actor()
    return render_template("dashboard.html", invoices=invoices, events=events[:6],
                           total=sum(r["amount"] for r in invoices),
                           pending=sum(r["status"] != "paid" for r in invoices))


@web.get("/invoices")
@login_required
def invoices():
    return render_template("invoices.html", invoices=company_invoices())


@web.get("/invoices/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    return render_template("invoice.html", invoice=authorize_invoice(invoice_id))


@web.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_invoice(invoice_id):
    if request.method == "POST":
        # Remove only the transport CSRF field. Reject all other unknown fields.
        data = {k: v for k, v in request.form.items() if k != "csrf_token"}
        update_invoice(invoice_id, data)
        flash("Invoice updated. The server verified company ownership and administrator permission.", "success")
        return redirect(url_for("web.invoice_detail", invoice_id=invoice_id))
    return render_template("edit.html", invoice=authorize_invoice(invoice_id, "update"))


@web.get("/security-monitoring")
@login_required
def monitoring():
    return render_template("monitoring.html", events=events_for_actor(200))


@web.get("/security-lab")
@login_required
def security_lab():
    enabled = current_app.config["LAB_MODE"] and current_app.config["SIMULATOR_ENABLED"]
    return render_template("lab.html", enabled=enabled, result=saved_result() if enabled and current_user.role == "admin" else None)


@web.post("/security-lab/run")
@login_required
def run_simulation():
    require_operator()
    from simulator.engine import run_scenarios, GROUPS
    group = request.form.get("group", "all")
    if group not in GROUPS:
        abort(400, description="Unknown scenario group.")
    lock = current_app.extensions["simulation_lock"]
    if not lock.acquire(blocking=False):
        abort(409, description="A demonstration is already running. Try again after it finishes.")
    try:
        result = run_scenarios(group)
        path = result_path()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
        temporary.replace(path)
        log_event("simulation", group, "run", "ALLOW", "disposable_local_http_run_completed")
    finally:
        lock.release()
    return redirect(url_for("web.test_results"))


@web.post("/security-lab/reset")
@login_required
def reset_demo():
    require_operator()
    lock = current_app.extensions["simulation_lock"]
    if not lock.acquire(blocking=False):
        abort(409, description="Wait for the current demonstration to finish.")
    try:
        reset_invoices()
        for path in Path(current_app.config["RESULTS_DIR"]).glob("result-*.json"):
            path.unlink()
        log_event("demo_dataset", None, "reset", "ALLOW", "fictional_invoices_restored_audit_retained")
    finally:
        lock.release()
    flash("All eight fictional invoices restored. Audit history was retained.", "success")
    return redirect(url_for("web.security_lab"))


@web.get("/test-results")
@login_required
def test_results():
    require_operator()
    return render_template("results.html", result=saved_result())
