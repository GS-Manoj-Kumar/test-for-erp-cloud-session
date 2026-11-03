# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CabinetProject(Document):
	def validate(self):
		self.project_name = (self.project_name or "").strip()
		if not self.project_type and self.client:
			self.project_type = frappe.db.get_value("Cabinet Client", self.client, "client_type")
		self.validate_dates()

	def validate_dates(self):
		if self.token_booking and self.advance_paid and getdate(self.advance_paid) < getdate(self.token_booking):
			frappe.throw(_("Advance Paid date cannot be before Token Booking date."))
		if (
			self.confirmation
			and self.actual_handover
			and getdate(self.actual_handover) < getdate(self.confirmation)
		):
			frappe.throw(_("Actual Handover date cannot be before Confirmation date."))
