# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from cabinet_erp.inventory.stock_logic import IN_PROCESS, RECEIVED, SENT, material_status

STATE_KEY = {RECEIVED: "received", IN_PROCESS: "in_process", SENT: "sent"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("production_order"):
		return columns(), []
	order = filters.production_order

	lines = frappe.get_all(
		"Order Material Line",
		filters={"parent": order, "parenttype": "Production Order"},
		fields=["stock_item", "description", "kind", "order_qty", "qty"],
		order_by="idx",
	)
	stock = {}
	for r in frappe.db.sql(
		"""select stock_item, state, sum(qty_change) as qty from `tabStock Ledger Entry`
		where production_order = %s group by stock_item, state""",
		order,
		as_dict=True,
	):
		stock.setdefault(r.stock_item, {})[STATE_KEY[r.state]] = r.qty

	return columns(), material_status(lines, stock)


def columns():
	return [
		{"fieldname": "stock_item", "label": _("Stock Item"), "fieldtype": "Link", "options": "Stock Item", "width": 140},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{"fieldname": "kind", "label": _("Kind"), "fieldtype": "Data", "width": 90},
		{"fieldname": "required", "label": _("Required"), "fieldtype": "Float", "width": 100},
		{"fieldname": "received", "label": _("Received"), "fieldtype": "Float", "width": 100},
		{"fieldname": "in_process", "label": _("In Process"), "fieldtype": "Float", "width": 100},
		{"fieldname": "sent", "label": _("Sent"), "fieldtype": "Float", "width": 100},
		{"fieldname": "shortfall", "label": _("Shortfall"), "fieldtype": "Float", "width": 100},
	]
