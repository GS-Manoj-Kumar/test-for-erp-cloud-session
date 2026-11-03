# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class StockItem(Document):
	def validate(self):
		self.item_code = (self.item_code or "").strip()
		self.item_name = (self.item_name or "").strip()
