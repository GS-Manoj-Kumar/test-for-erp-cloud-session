"""Frappe CRM integration: when a CRM Deal is marked Won, offer to create / link a Cabinet Client."""

import frappe
from frappe import _

from cabinet_erp.clients.crm_logic import became_won, client_values_from_deal, primary_contact_of

DEAL_FIELD = "cabinet_client"


def on_deal_update(doc, method=None):
	"""doc_events hook for CRM Deal (on_update)."""
	before = doc.get_doc_before_save()
	if not became_won(before.status if before else None, doc.status) or doc.get(DEAL_FIELD):
		return

	# An organization that is already a client: just link it.
	if doc.get("organization"):
		existing = frappe.db.get_value("Cabinet Client", {"crm_organization": doc.organization})
		if existing:
			doc.db_set(DEAL_FIELD, existing, update_modified=False)
			frappe.msgprint(_("Deal won. Linked to existing Cabinet Client {0}.").format(existing), alert=True)
			return

	frappe.msgprint(
		_("Deal {0} is won. Create a Cabinet Client for it?").format(doc.name),
		title=_("Deal Won"),
		primary_action={
			"label": _("Create Cabinet Client"),
			"server_action": "cabinet_erp.clients.crm_glue.make_client_from_deal",
			"args": {"deal": doc.name},
		},
	)
	# A to-do as well, so the offer isn't lost when the deal is won from the CRM UI.
	owner = doc.get("deal_owner") or frappe.session.user
	if not frappe.db.exists("ToDo", {"reference_type": doc.doctype, "reference_name": doc.name, "status": "Open"}):
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": owner,
				"reference_type": doc.doctype,
				"reference_name": doc.name,
				"description": _("Deal {0} won: create the Cabinet Client (open the deal and click Create Cabinet Client).").format(doc.name),
			}
		).insert(ignore_permissions=True)


@frappe.whitelist()
def make_client_from_deal(deal):
	"""Create (or return the already linked) Cabinet Client for a deal, and link it back."""
	frappe.has_permission("Cabinet Client", "create", throw=True)
	if isinstance(deal, dict):  # msgprint server_action passes args as a dict
		deal = deal.get("deal")
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission("read")
	if d.get(DEAL_FIELD):
		return d.get(DEAL_FIELD)

	org = frappe.db.get_value("CRM Organization", d.organization, ["organization_name"], as_dict=True) if d.get("organization") else None
	contacts = [c.as_dict() for c in (d.get("contacts") or [])]
	values = client_values_from_deal(d.as_dict(), org, primary_contact_of(contacts))
	client = frappe.get_doc({"doctype": "Cabinet Client", **values}).insert()
	d.db_set(DEAL_FIELD, client.name, update_modified=False)
	frappe.db.set_value("ToDo", {"reference_type": "CRM Deal", "reference_name": d.name, "status": "Open"}, "status", "Closed")
	frappe.msgprint(_("Cabinet Client {0} created.").format(client.name), alert=True)
	return client.name
