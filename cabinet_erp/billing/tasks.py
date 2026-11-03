import frappe
from frappe.utils import nowdate

from cabinet_erp.billing.doctype.cabinet_invoice.cabinet_invoice import update_invoice_balance


def mark_overdue():
	"""Daily: move unpaid Tax Invoices past their due date to Overdue."""
	for name in frappe.get_all(
		"Cabinet Invoice",
		filters={
			"docstatus": 1,
			"invoice_type": "Tax Invoice",
			"outstanding_amount": (">", 0),
			"due_date": ("<", nowdate()),
			"status": ("!=", "Overdue"),
		},
		pluck="name",
	):
		update_invoice_balance(name)
	frappe.db.commit()
