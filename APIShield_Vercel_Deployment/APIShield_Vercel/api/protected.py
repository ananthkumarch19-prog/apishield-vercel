from flask import Blueprint, jsonify, request
from security.authorization import authorize_invoice, company_invoices
from security.invoices import serialize_invoice, update_invoice

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/invoices")
def list_invoices():
    return jsonify(invoices=[serialize_invoice(row) for row in company_invoices()])


@api.get("/invoices/<int:invoice_id>")
def read_invoice(invoice_id):
    row = authorize_invoice(invoice_id)
    return jsonify(invoice=serialize_invoice(row), reason="same_company_and_permitted_role")


@api.patch("/invoices/<int:invoice_id>")
def patch_invoice(invoice_id):
    # Identity/ownership/role are checked before validation or serialization.
    row = update_invoice(invoice_id, request.get_json(silent=True))
    return jsonify(invoice=serialize_invoice(row), reason="same_company_and_permitted_role")
