# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from cabinet_erp.billing.billing_logic import payment_errors
from cabinet_erp.billing.doctype.cabinet_invoice.cabinet_invoice import (
	fresh_outstanding,
	lock_invoice,
	update_invoice_balance,
)


class PaymentEntryLite(Document):
	def validate(self):
		if self.mode != "Cash" and not (self.reference_no or "").strip():
			frappe.throw(_("Reference No is required for {0} payments.").format(self.mode))
		self.check_against_invoice(lock=False)

	def before_submit(self):
		self.check_against_invoice(lock=True)

	def check_against_invoice(self, lock):
		inv = lock_invoice(self.invoice) if lock else frappe.db.get_value(
			"Cabinet Invoice", self.invoice, ["name", "client", "invoice_type", "docstatus", "rounded_total"], as_dict=True
		)
		if not inv:
			frappe.throw(_("Invoice {0} not found.").format(self.invoice))
		self.invoice_outstanding = fresh_outstanding(inv)
		errors = payment_errors(
			self.amount,
			self.invoice_outstanding,
			invoice_type=inv.invoice_type,
			invoice_docstatus=inv.docstatus,
			invoice_client=inv.client,
			client=self.client,
		)
		if errors:
			frappe.throw("<br>".join(errors), title=_("Cannot record payment"))

	def on_submit(self):
		update_invoice_balance(self.invoice)

	def on_cancel(self):
		update_invoice_balance(self.invoice)
