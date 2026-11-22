"""INTENTIONALLY VULNERABLE. Never register this blueprint outside local lab mode.

Authentication and CSRF still apply. The missing ownership / role check is the
specific flaw being demonstrated. This is not reusable application code.
"""
from flask import Blueprint, abort, jsonify, request
from database.db import get_db, is_demo_database
from security.audit import log_event
from security.invoices import serialize_invoice, update_invoice

lab = Blueprint("lab", __name__, url_prefix="/lab")


@lab.before_request
def require_fictional_dataset():
    if not is_demo_database():
        abort(404)


@lab.get("/invoices/<int:invoice_id>")
def vulnerable_read(invoice_id):
    # BOLA: a valid login does not establish ownership of this object.
    row = None if invoice_id > 9223372036854775807 else get_db().execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if row is None:
        log_event("invoice", invoice_id, "read", "DENY", "resource_not_found")
        abort(404, description="resource_not_found")
    log_event("invoice", invoice_id, "read", "LAB_BYPASS", "lab_missing_object_check")
    return jsonify(invoice=serialize_invoice(row), reason="lab_missing_object_check", warning="Fictional local lab: authorization deliberately bypassed")


@lab.patch("/invoices/<int:invoice_id>")
def vulnerable_update(invoice_id):
    row = update_invoice(invoice_id, request.get_json(silent=True), vulnerable=True)
    return jsonify(invoice=serialize_invoice(row), reason="lab_missing_object_and_role_checks", warning="Fictional local lab: authorization deliberately bypassed")
