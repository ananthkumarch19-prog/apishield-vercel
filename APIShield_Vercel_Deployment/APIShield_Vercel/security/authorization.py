"""One deny-by-default policy for protected API AND server-rendered pages."""
from flask import abort
from flask_login import current_user
from database.db import get_db
from security.audit import log_event

ROLE_ACTIONS = {"employee": frozenset({"read", "list"}), "admin": frozenset({"read", "list", "update"})}


def policy(user, invoice_company_id, action):
    if not user.is_authenticated:
        return False, "authentication_required"
    if user.company_id != invoice_company_id:
        return False, "company_mismatch"
    if action not in ROLE_ACTIONS.get(user.role, frozenset()):
        return False, "role_not_permitted"
    return True, "same_company_and_permitted_role"


def authorize_invoice(invoice_id, action="read", *, audit_allow=True):
    if not current_user.is_authenticated:
        log_event("invoice", invoice_id, action, "DENY", "authentication_required")
        abort(401, description="authentication_required")
    # SQLite signed integers cannot represent arbitrarily large URL integers.
    invoice = None if invoice_id > 9223372036854775807 else get_db().execute(
        "SELECT * FROM invoices WHERE id=?", (invoice_id,)
    ).fetchone()
    if invoice is None:
        log_event("invoice", invoice_id, action, "DENY", "resource_not_found")
        abort(404, description="resource_not_found")
    allowed, reason = policy(current_user, invoice["company_id"], action)
    if not allowed:
        log_event("invoice", invoice_id, action, "DENY", reason)
        abort(403, description=reason)
    if audit_allow:
        log_event("invoice", invoice_id, action, "ALLOW", reason)
    return invoice


def company_invoices():
    allowed, reason = policy(current_user, getattr(current_user, "company_id", None), "list")
    if not allowed:
        log_event("invoice_collection", None, "list", "DENY", reason)
        abort(401 if not current_user.is_authenticated else 403, description=reason)
    # A filtered query prevents accidental leakage through list and overview pages.
    rows = get_db().execute("SELECT * FROM invoices WHERE company_id=? ORDER BY id", (current_user.company_id,)).fetchall()
    log_event("invoice_collection", None, "list", "ALLOW", reason)
    return rows
