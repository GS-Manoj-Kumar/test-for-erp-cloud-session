# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from cabinet_erp.inventory.stock_logic import SCOPE_LINK, location_errors, location_title


class StockLocation(Document):
	def validate(self):
		self.fill_parents()
		errors = location_errors(self.scope, self.client, self.project, self.production_order)
		if errors:
			frappe.throw("<br>".join(errors))
		self.validate_unique()
		self.title = location_title(
			self.scope, self.client, self.project, self.production_order, names=self.display_names()
		)

	def fill_parents(self):
		"""Order -> its project and client; Project -> its client. Unused links are cleared."""
		if self.scope == "General":
			self.client = self.project = self.production_order = None
		elif self.scope == "Client":
			self.project = self.production_order = None
		elif self.scope == "Project":
			self.production_order = None
			if self.project:
				self.client = frappe.db.get_value("Cabinet Project", self.project, "client")
		elif self.scope == "Order" and self.production_order:
			self.project, self.client = frappe.db.get_value(
				"Production Order", self.production_order, ["project", "client"]
			) or (None, None)

	def validate_unique(self):
		link = SCOPE_LINK.get(self.scope)
		filters = {"scope": self.scope, "name": ("!=", self.name or "")}
		if link:
			filters[link] = self.get(link)
		existing = frappe.db.get_value("Stock Location", filters)
		if existing:
			frappe.throw(_("A {0} location already exists for this: {1}").format(self.scope, existing))

	def display_names(self):
		names = {}
		if self.client:
			names[self.client] = frappe.db.get_value("Cabinet Client", self.client, "client_name")
		if self.project:
			names[self.project] = frappe.db.get_value("Cabinet Project", self.project, "project_name")
		if self.production_order:
			names[self.production_order] = frappe.db.get_value(
				"Production Order", self.production_order, "order_title"
			)
		return names


def get_or_create_location(scope, link_value=None):
	"""Find the location for a scope (+ client/project/order id), creating it if missing."""
	link = SCOPE_LINK[scope]
	filters = {"scope": scope}
	if link:
		filters[link] = link_value
	name = frappe.db.get_value("Stock Location", filters)
	if name:
		return name
	doc = frappe.get_doc(dict(filters, doctype="Stock Location"))
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def location_for(scope, link_value=None):
	frappe.has_permission("Stock Location", "create", throw=True)
	return get_or_create_location(scope, link_value)
