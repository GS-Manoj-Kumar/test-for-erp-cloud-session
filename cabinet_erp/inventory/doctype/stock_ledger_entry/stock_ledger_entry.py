# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StockLedgerEntry(Document):
	"""Append-only. Rows are written by Stock Movement submit/cancel and never changed."""

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Stock Ledger Entries cannot be edited."))

	def on_trash(self):
		frappe.throw(_("Stock Ledger Entries cannot be deleted. Cancel the Stock Movement instead."))
