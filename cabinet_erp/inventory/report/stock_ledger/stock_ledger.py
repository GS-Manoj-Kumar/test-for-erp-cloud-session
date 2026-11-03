# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from cabinet_erp.inventory.stock_logic import ledger_conditions, running_balances


def execute(filters=None):
	filters = frappe._dict(filters or {})
	where, params = ledger_conditions(filters)
	rows = frappe.db.sql(
		f"""select posting_date, movement, movement_type, is_cancellation, location, stock_item,
			state, qty_change, rate
		from `tabStock Ledger Entry` where {where}
		order by posting_date, creation""",
		params,
		as_dict=True,
	)
	data = running_balances(opening_balances(filters), rows)

	titles = dict(frappe.get_all("Stock Location", fields=["name", "title"], as_list=1))
	for r in data:
		r["location_title"] = titles.get(r["location"], "")
	return columns(), data


def opening_balances(filters):
	"""Balances before from_date for the same filters, so the running balance is right."""
	if not filters.get("from_date"):
		return {}
	where, params = ledger_conditions(filters, from_date=False, to_date=False)
	params["opening_date"] = filters.from_date
	rows = frappe.db.sql(
		f"""select location, state, stock_item, sum(qty_change) as qty
		from `tabStock Ledger Entry` where {where} and posting_date < %(opening_date)s
		group by location, state, stock_item""",
		params,
		as_dict=True,
	)
	return {(r.location, r.state, r.stock_item): r.qty for r in rows}


def columns():
	return [
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "movement", "label": _("Movement"), "fieldtype": "Link", "options": "Stock Movement", "width": 140},
		{"fieldname": "movement_type", "label": _("Type"), "fieldtype": "Data", "width": 150},
		{"fieldname": "is_cancellation", "label": _("Cancel Row"), "fieldtype": "Check", "width": 90},
		{"fieldname": "location", "label": _("Location"), "fieldtype": "Link", "options": "Stock Location", "width": 110},
		{"fieldname": "location_title", "label": _("Location Title"), "fieldtype": "Data", "width": 200},
		{"fieldname": "stock_item", "label": _("Stock Item"), "fieldtype": "Link", "options": "Stock Item", "width": 140},
		{"fieldname": "state", "label": _("State"), "fieldtype": "Data", "width": 100},
		{"fieldname": "qty_change", "label": _("Qty Change"), "fieldtype": "Float", "width": 100},
		{"fieldname": "balance", "label": _("Balance"), "fieldtype": "Float", "width": 100},
		{"fieldname": "rate", "label": _("Rate"), "fieldtype": "Currency", "width": 100},
	]
