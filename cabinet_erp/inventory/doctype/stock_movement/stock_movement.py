# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from cabinet_erp.inventory.stock_logic import (
	TRANSFER,
	movement_errors,
	movement_legs,
	needs_urgent_approval,
	reverse_legs,
	shortage_errors,
)


class StockMovement(Document):
	def validate(self):
		if self.movement_type != TRANSFER:
			self.target_location = None
			self.is_urgent = 0
			self.reason = None
		if self.movement_type != "Dispatch":
			self.from_state = None
		self.set_rates_and_totals()

		errors = movement_errors(
			self.movement_type,
			self.location,
			target_location=self.target_location,
			from_state=self.from_state,
			items=[d.as_dict() for d in self.items],
			location_project=self.project_of(self.location),
			target_project=self.project_of(self.target_location),
			is_urgent=self.is_urgent,
			reason=self.reason,
		)
		for loc in filter(None, (self.location, self.target_location)):
			if frappe.db.get_value("Stock Location", loc, "disabled"):
				errors.append(_("Location {0} is disabled.").format(loc))
		if errors:
			frappe.throw("<br>".join(errors), title=_("Cannot save Stock Movement"))

	def set_rates_and_totals(self):
		for d in self.items:
			if not d.rate and d.stock_item:
				d.rate = frappe.db.get_value("Stock Item", d.stock_item, "default_rate") or 0
			d.amount = flt(d.qty) * flt(d.rate)
		self.total_qty = sum(flt(d.qty) for d in self.items)
		self.total_amount = sum(flt(d.amount) for d in self.items)

	@staticmethod
	def project_of(location):
		return frappe.db.get_value("Stock Location", location, "project") if location else None

	def before_submit(self):
		if self.movement_type == TRANSFER and needs_urgent_approval(
			self.project_of(self.location), self.project_of(self.target_location)
		):
			self.approver = frappe.session.user

	def legs(self):
		return movement_legs(
			self.movement_type,
			self.location,
			[d.as_dict() for d in self.items],
			target_location=self.target_location,
			from_state=self.from_state,
		)

	def on_submit(self):
		self.post(self.legs(), is_cancellation=0)

	def before_cancel(self):
		# ledger rows point at this movement but must stay; don't let them block cancel
		self.ignore_linked_doctypes = ("Stock Ledger Entry",)

	def on_cancel(self):
		self.post(reverse_legs(self.legs()), is_cancellation=1)

	def post(self, legs, is_cancellation):
		lock_locations({l["location"] for l in legs})
		errors = shortage_errors(legs, get_balance)
		if errors:
			frappe.throw("<br>".join(errors), title=_("Not enough stock"))
		scope_cache = {}
		for leg in legs:
			loc = leg["location"]
			if loc not in scope_cache:
				scope_cache[loc] = frappe.db.get_value(
					"Stock Location", loc, ["client", "project", "production_order"], as_dict=True
				)
			frappe.get_doc(
				{
					"doctype": "Stock Ledger Entry",
					"posting_date": self.posting_date,
					"voucher_type": self.doctype,
					"movement": self.name,
					"movement_type": self.movement_type,
					"is_cancellation": is_cancellation,
					**leg,
					**scope_cache[loc],
				}
			).insert(ignore_permissions=True)


def lock_locations(locations):
	"""Row-lock the locations so two movements on the same stock can't race."""
	if locations:
		frappe.db.sql(
			"select name from `tabStock Location` where name in %(names)s for update",
			{"names": tuple(locations)},
		)


def get_balance(location, state, stock_item):
	return flt(
		frappe.db.sql(
			"""select coalesce(sum(qty_change), 0) from `tabStock Ledger Entry`
			where location=%s and state=%s and stock_item=%s""",
			(location, state, stock_item),
		)[0][0]
	)
