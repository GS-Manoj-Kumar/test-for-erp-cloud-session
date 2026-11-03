# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from cabinet_erp.utils.gst import gstin_error, normalize_gstin, state_from_gstin


class CabinetClient(Document):
	def validate(self):
		self.client_name = (self.client_name or "").strip()
		self.validate_gstin()

	def validate_gstin(self):
		if self.client_type != "B2B":
			# GSTIN is a B2B-only field; drop anything left over from a type change.
			self.gstin = None
			return
		if not self.gstin:
			return
		self.gstin = normalize_gstin(self.gstin)
		error = gstin_error(self.gstin)
		if error:
			frappe.throw(_(error), title=_("Invalid GSTIN"))
		if not self.state:
			self.state = state_from_gstin(self.gstin)
		elif self.state != state_from_gstin(self.gstin):
			frappe.msgprint(
				_("GSTIN belongs to {0} but State is set to {1}.").format(
					state_from_gstin(self.gstin), self.state
				),
				indicator="orange",
				alert=True,
			)
