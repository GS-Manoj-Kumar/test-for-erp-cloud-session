# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from cabinet_erp.production.f4p_import import (
	PANEL_FIELDS,
	F4PError,
	meta_warnings,
	order_values,
	parse_f4p,
	plan_import,
)


class ProductionOrder(Document):
	def validate(self):
		if not self.order_title:
			self.order_title = self.project_name or self.project

	def on_trash(self):
		frappe.db.delete("Order Panel", {"production_order": self.name})

	@frappe.whitelist()
	def import_f4p(self, file_url):
		"""Import a sealed f4p.sqlite (already uploaded as a File) into this order.

		Same seal_id as already imported -> nothing changes.
		Different seal_id -> panels and material lines are replaced (latest seal wins).
		"""
		self.check_permission("write")
		if self.status == "Cancelled":
			frappe.throw(_("Cannot import into a Cancelled order."))

		file_doc = frappe.get_doc("File", {"file_url": file_url})
		try:
			parsed = parse_f4p(file_doc.get_full_path())
		except F4PError as e:
			frappe.throw(str(e), title=_("F4P import failed"))

		action = plan_import(self.seal_id, parsed)
		if action == "skip":
			return {"action": "skip", "seal_id": parsed["seal_id"], "warnings": []}

		warnings = meta_warnings(parsed, project=self.project, client=self.client, order=self.name)

		self.update(order_values(parsed))
		self.f4p_file = file_url
		self.f4p_warnings = "\n".join(warnings)
		self.set("material_lines", [])
		for line in parsed["material_lines"]:
			self.append("material_lines", line)
		self.save()

		frappe.db.delete("Order Panel", {"production_order": self.name})
		for panel in parsed["panels"]:
			row = frappe.new_doc("Order Panel")
			row.production_order = self.name
			row.update({k: panel[k] for k in PANEL_FIELDS})
			row.insert(ignore_permissions=True)

		if file_doc.attached_to_name != self.name:
			file_doc.db_set({"attached_to_doctype": self.doctype, "attached_to_name": self.name})

		return {
			"action": action,
			"seal_id": parsed["seal_id"],
			"panels": len(parsed["panels"]),
			"material_lines": len(parsed["material_lines"]),
			"warnings": warnings,
		}
