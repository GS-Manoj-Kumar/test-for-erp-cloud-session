# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from cabinet_erp.billing.billing_logic import project_summary


def execute(filters=None):
	filters = frappe._dict(filters or {})
	inv_filters = {"docstatus": 1, "invoice_type": ("in", ["Tax Invoice", "Credit Note"]), "project": ("is", "set")}
	proj_filters = {}
	if filters.get("client"):
		inv_filters["client"] = proj_filters["client"] = filters.client
	if filters.get("project"):
		inv_filters["project"] = filters.project
		proj_filters["name"] = filters.project
	if filters.get("from_date") and filters.get("to_date"):
		inv_filters["posting_date"] = ("between", [filters.from_date, filters.to_date])

	invoices = frappe.get_all(
		"Cabinet Invoice",
		filters=inv_filters,
		fields=["project", "invoice_type", "net_total", "rounded_total", "paid_amount", "outstanding_amount"],
	)
	projects = frappe.get_all("Cabinet Project", filters=proj_filters, fields=["name", "project_name", "client"])
	info = {p.name: p for p in projects}

	order_costs = {}
	if info:
		for r in frappe.get_all(
			"Production Order",
			filters={"project": ("in", list(info)), "status": ("!=", "Cancelled")},
			fields=["project", "sum(cost_grand) as cost"],
			group_by="project",
		):
			order_costs[r.project] = r.cost or 0

	data = [r for r in project_summary(invoices, order_costs) if r["project"] in info]
	for r in data:
		r["project_name"] = info[r["project"]].project_name
		r["client"] = info[r["project"]].client
	return columns(), data


def columns():
	cur = lambda f, l: {"fieldname": f, "label": _(l), "fieldtype": "Currency", "width": 120}
	return [
		{"fieldname": "project", "label": _("Project"), "fieldtype": "Link", "options": "Cabinet Project", "width": 80},
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 170},
		{"fieldname": "client", "label": _("Client"), "fieldtype": "Link", "options": "Cabinet Client", "width": 80},
		cur("invoiced", "Invoiced (incl. GST)"),
		cur("invoiced_net", "Invoiced (excl. GST)"),
		cur("paid", "Paid"),
		cur("outstanding", "Outstanding"),
		cur("order_cost", "Order Cost"),
		cur("margin", "Margin"),
		{"fieldname": "margin_pct", "label": _("Margin %"), "fieldtype": "Percent", "width": 90},
	]
