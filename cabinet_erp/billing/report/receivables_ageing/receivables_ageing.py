# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate

from cabinet_erp.billing.billing_logic import AGEING_BUCKETS, ageing_row, bucket_field


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_of = filters.get("as_of") or nowdate()
	conditions = {
		"docstatus": 1,
		"invoice_type": "Tax Invoice",
		"outstanding_amount": (">", 0),
		"posting_date": ("<=", as_of),
	}
	for key in ("client", "project"):
		if filters.get(key):
			conditions[key] = filters[key]
	invoices = frappe.get_all(
		"Cabinet Invoice",
		filters=conditions,
		fields=["name", "client", "client_name", "project", "posting_date", "due_date", "rounded_total",
			"outstanding_amount"],
		order_by="due_date, name",
	)
	return columns(), [ageing_row(inv, as_of) for inv in invoices]


def columns():
	cols = [
		{"fieldname": "name", "label": _("Invoice"), "fieldtype": "Link", "options": "Cabinet Invoice", "width": 130},
		{"fieldname": "client", "label": _("Client"), "fieldtype": "Link", "options": "Cabinet Client", "width": 80},
		{"fieldname": "client_name", "label": _("Client Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Cabinet Project", "width": 80},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 95},
		{"fieldname": "due_date", "label": _("Due"), "fieldtype": "Date", "width": 95},
		{"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 100},
		{"fieldname": "rounded_total", "label": _("Invoice Total"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "outstanding_amount", "label": _("Outstanding"), "fieldtype": "Currency", "width": 110},
	]
	for label, _lo, _hi in AGEING_BUCKETS:
		cols.append({"fieldname": bucket_field(label), "label": label, "fieldtype": "Currency", "width": 100})
	return cols
