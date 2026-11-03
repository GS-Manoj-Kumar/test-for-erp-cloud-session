# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from cabinet_erp.inventory.stock_logic import ledger_conditions, pivot_balances


def execute(filters=None):
	filters = frappe._dict(filters or {})
	where, params = ledger_conditions(filters, from_date=False)
	rows = frappe.db.sql(
		f"""select location, stock_item, state, sum(qty_change) as qty
		from `tabStock Ledger Entry` where {where}
		group by location, stock_item, state""",
		params,
		as_dict=True,
	)
	data = pivot_balances(rows)
	add_names(data)
	return columns(), data


def add_names(data):
	locs = {r["location"] for r in data}
	items = {r["stock_item"] for r in data}
	loc_title = dict(frappe.get_all("Stock Location", {"name": ("in", list(locs))}, ["name", "title"], as_list=1)) if locs else {}
	item_info = {
		i.name: i
		for i in frappe.get_all("Stock Item", {"name": ("in", list(items))}, ["name", "item_name", "uom"])
	} if items else {}
	for r in data:
		r["location_title"] = loc_title.get(r["location"], "")
		info = item_info.get(r["stock_item"]) or {}
		r["item_name"] = info.get("item_name", "")
		r["uom"] = info.get("uom", "")


def columns():
	return [
		{"fieldname": "location", "label": _("Location"), "fieldtype": "Link", "options": "Stock Location", "width": 110},
		{"fieldname": "location_title", "label": _("Location Title"), "fieldtype": "Data", "width": 220},
		{"fieldname": "stock_item", "label": _("Stock Item"), "fieldtype": "Link", "options": "Stock Item", "width": 140},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Data", "width": 60},
		{"fieldname": "received", "label": _("Received"), "fieldtype": "Float", "width": 100},
		{"fieldname": "in_process", "label": _("In Process"), "fieldtype": "Float", "width": 100},
		{"fieldname": "sent", "label": _("Sent"), "fieldtype": "Float", "width": 100},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Float", "width": 100},
	]
