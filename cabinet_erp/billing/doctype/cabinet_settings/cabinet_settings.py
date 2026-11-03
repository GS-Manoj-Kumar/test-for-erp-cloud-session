# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from cabinet_erp.utils.gst import gstin_error, normalize_gstin


class CabinetSettings(Document):
	def validate(self):
		if self.company_gstin:
			self.company_gstin = normalize_gstin(self.company_gstin)
			error = gstin_error(self.company_gstin)
			if error:
				frappe.throw(_(error), title=_("Invalid GSTIN"))
