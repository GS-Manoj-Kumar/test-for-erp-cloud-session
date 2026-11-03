# Copyright (c) 2026, Cabinet ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate

from cabinet_erp.billing.billing_logic import (
	CREDIT_NOTE,
	TAX_INVOICE,
	BillingError,
	compute_invoice,
	credit_note_errors,
	invoice_status,
	order_invoice_items,
	outstanding,
)


class CabinetInvoice(Document):
	def validate(self):
		settings = frappe.get_cached_doc("Cabinet Settings")
		if not settings.company_state:
			frappe.throw(_("Set Company State in Cabinet Settings first (needed for GST)."))
		self.company_state = settings.company_state

		self.validate_links()
		if self.invoice_type != CREDIT_NOTE:
			self.return_against = None
		if self.invoice_type == TAX_INVOICE:
			if not self.due_date:
				self.due_date = add_days(self.posting_date, settings.default_due_days or 0)
			if getdate(self.due_date) < getdate(self.posting_date):
				frappe.throw(_("Due Date cannot be before Posting Date."))
		else:
			self.due_date = None
		if not self.place_of_supply:
			self.place_of_supply = frappe.db.get_value("Cabinet Client", self.client, "state") or self.company_state

		self.calculate_totals()
		self.paid_amount = self.credited_amount = 0
		self.outstanding_amount = self.rounded_total if self.invoice_type == TAX_INVOICE else 0
		self.status = "Draft"

	def validate_links(self):
		if self.production_order:
			order_project = frappe.db.get_value("Production Order", self.production_order, "project")
			if not self.project:
				self.project = order_project
			elif order_project != self.project:
				frappe.throw(_("Order {0} is not part of project {1}.").format(self.production_order, self.project))
		if self.project:
			project_client = frappe.db.get_value("Cabinet Project", self.project, "client")
			if project_client != self.client:
				frappe.throw(_("Project {0} belongs to client {1}, not {2}.").format(self.project, project_client, self.client))

	def calculate_totals(self):
		try:
			res = compute_invoice([d.as_dict() for d in self.items], self.company_state, self.place_of_supply)
		except BillingError as e:
			frappe.throw(str(e))
		for d, amount in zip(self.items, res.pop("amounts")):
			d.amount = amount
		self.update(res)

	def before_submit(self):
		if self.invoice_type == CREDIT_NOTE:
			original = lock_invoice(self.return_against)
			errors = credit_note_errors(
				self.rounded_total,
				fresh_outstanding(original),
				original.invoice_type,
				original.docstatus,
				original_client=original.client,
				client=self.client,
			)
			if errors:
				frappe.throw("<br>".join(errors), title=_("Cannot submit Credit Note"))

	def on_submit(self):
		update_invoice_balance(self.name)
		if self.invoice_type == CREDIT_NOTE:
			update_invoice_balance(self.return_against)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if self.invoice_type == CREDIT_NOTE:
			update_invoice_balance(self.return_against)


def lock_invoice(name):
	row = frappe.db.sql(
		"""select name, client, invoice_type, docstatus, rounded_total
		from `tabCabinet Invoice` where name=%s for update""",
		name,
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Invoice {0} not found.").format(name))
	return row[0]


def paid_and_credited(name):
	paid = frappe.db.sql(
		"select coalesce(sum(amount), 0) from `tabPayment Entry Lite` where invoice=%s and docstatus=1", name
	)[0][0]
	credited = frappe.db.sql(
		"""select coalesce(sum(rounded_total), 0) from `tabCabinet Invoice`
		where return_against=%s and invoice_type=%s and docstatus=1""",
		(name, CREDIT_NOTE),
	)[0][0]
	return flt(paid), flt(credited)


def fresh_outstanding(invoice_row):
	paid, credited = paid_and_credited(invoice_row.name)
	return outstanding(invoice_row.rounded_total, paid, credited)


def update_invoice_balance(name):
	"""Recompute paid / credited / outstanding / status from submitted payments and credit notes."""
	inv = frappe.db.get_value(
		"Cabinet Invoice", name, ["name", "docstatus", "invoice_type", "rounded_total", "due_date"], as_dict=True
	)
	if inv.invoice_type == TAX_INVOICE:
		paid, credited = paid_and_credited(name)
	else:
		paid = credited = 0
	values = {
		"paid_amount": paid,
		"credited_amount": credited,
		"outstanding_amount": outstanding(inv.rounded_total, paid, credited) if inv.invoice_type == TAX_INVOICE else 0,
		"status": invoice_status(
			inv.docstatus, inv.invoice_type, inv.rounded_total, paid, credited, inv.due_date, nowdate()
		),
	}
	frappe.db.set_value("Cabinet Invoice", name, values, update_modified=False)
	return values


@frappe.whitelist()
def get_order_items(production_order, mode="lines"):
	"""Rows for "Make from Order": material lines, or one lump-sum line at cost_grand."""
	order = frappe.get_doc("Production Order", production_order)
	order.check_permission("read")
	gst_rate = int(frappe.db.get_single_value("Cabinet Settings", "default_gst_rate") or 18)
	try:
		return order_invoice_items(
			order.as_dict(), [d.as_dict() for d in order.material_lines], mode=mode, gst_rate=gst_rate
		)
	except BillingError as e:
		frappe.throw(str(e))
