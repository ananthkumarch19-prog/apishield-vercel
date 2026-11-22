from decimal import Decimal, InvalidOperation
from flask import abort
from werkzeug.exceptions import HTTPException
from database.db import get_db
from security.audit import log_event
from security.authorization import authorize_invoice


def serialize_invoice(row):
    return {"id": row["id"], "company_id": row["company_id"], "invoice_number": row["invoice_number"],
            "customer_name": row["customer_name"], "amount": f"{Decimal(row['amount']) / 100:.2f}",
            "currency": "INR", "status": row["status"], "created_at": row["created_at"]}


def validate_changes(data):
    if not isinstance(data, dict) or not data:
        abort(400, description="A nonempty JSON object is required.")
    if set(data) - {"customer_name", "amount", "status"}:
        abort(400, description="Only customer_name, amount and status may be changed.")
    result = {}
    if "customer_name" in data:
        name = data["customer_name"]
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name):
            abort(400, description="Customer name must contain 1 to 100 printable characters.")
        result["customer_name"] = name.strip()
    if "status" in data:
        if not isinstance(data["status"], str) or data["status"] not in {"pending", "paid", "overdue"}:
            abort(400, description="Status must be pending, paid or overdue.")
        result["status"] = data["status"]
    if "amount" in data:
        try:
            if isinstance(data["amount"], bool) or not isinstance(data["amount"], (str, int, float)):
                raise ValueError
            amount = Decimal(str(data["amount"]))
            if not amount.is_finite() or amount < 0 or amount > 1000000000 or amount != amount.quantize(Decimal("0.01")):
                raise ValueError
            result["amount"] = int(amount * 100)
        except (InvalidOperation, ValueError):
            abort(400, description="Amount must be 0 to 1,000,000,000 INR with at most two decimals.")
    return result


def update_invoice(invoice_id, data, *, vulnerable=False):
    if vulnerable:
        # This branch is called ONLY from the explicitly gated educational blueprint.
        invoice = None if invoice_id > 9223372036854775807 else get_db().execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if invoice is None:
            abort(404, description="resource_not_found")
    else:
        invoice = authorize_invoice(invoice_id, "update", audit_allow=False)
    try:
        changes = validate_changes(data)
    except HTTPException:
        log_event("invoice", invoice_id, "update", "DENY", "invalid_update_payload")
        raise
    db = get_db()
    # Column names originate ONLY from the fixed validator allowlist. Values use placeholders.
    assignments = ", ".join(f"{key}=?" for key in changes)
    with db:
        db.execute(f"UPDATE invoices SET {assignments} WHERE id=? AND company_id=?",
                   (*changes.values(), invoice_id, invoice["company_id"]))
        log_event("invoice", invoice_id, "update", "LAB_BYPASS" if vulnerable else "ALLOW",
                  "lab_missing_object_and_role_checks" if vulnerable else "same_company_and_permitted_role",
                  commit=False)
    return db.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
