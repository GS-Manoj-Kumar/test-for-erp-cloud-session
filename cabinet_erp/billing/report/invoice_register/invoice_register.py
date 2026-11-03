# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

AMOUNT_FIELDS = ("net_total", "cgst", "sgst", "igst", "total_tax", "rounded_total", "paid_amount", "outstanding_amount")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = {"posting_date": ("between", [filters.from_date, filters.to_date])}
	for key in ("client", "project", "production_order", "invoice_type"):
		if filters.get(key):
			conditions[key] = filters[key]
	if filters.get("status"):
		conditions["status"] = filters.status
	else:
		conditions["docstatus"] = ("<", 2)

	data = frappe.get_all(
		"Cabinet Invoice",
		filters=conditions,
		fields=["name", "posting_date", "invoice_type", "status", "client", "client_name", "project",
			"production_order", "due_date", *AMOUNT_FIELDS],
		order_by="posting_date, name",
	)
	for r in data:
		if r.invoice_type == "Credit Note":
			# credit notes reduce the totals row
			for f in AMOUNT_FIELDS:
				r[f] = -(r[f] or 0)
	return columns(), data


def columns():
	cur = lambda f, l: {"fieldname": f, "label": _(l), "fieldtype": "Currency", "width": 110}
	return [
		{"fieldname": "name", "label": _("Invoice"), "fieldtype": "Link", "options": "Cabinet Invoice", "width": 130},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
		{"fieldname": "invoice_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "client", "label": _("Client"), "fieldtype": "Link", "options": "Cabinet Client", "width": 80},
		{"fieldname": "client_name", "label": _("Client Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Cabinet Project", "width": 80},
		{"fieldname": "production_order", "label": _("Order"), "fieldtype": "Link", "options": "Production Order", "width": 120},
		{"fieldname": "due_date", "label": _("Due"), "fieldtype": "Date", "width": 95},
		cur("net_total", "Net"),
		cur("cgst", "CGST"),
		cur("sgst", "SGST"),
		cur("igst", "IGST"),
		cur("total_tax", "Tax"),
		cur("rounded_total", "Total"),
		cur("paid_amount", "Paid"),
		cur("outstanding_amount", "Outstanding"),
	]
