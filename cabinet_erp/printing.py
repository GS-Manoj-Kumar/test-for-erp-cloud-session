"""Frappe glue for the PDF / print formats.

Each Print Format's HTML is just:
    {% set p = cabinet_print(doc) %}{% include "cabinet_erp/templates/print/<template>.html" %}
`cabinet_print` is registered as a Jinja method in hooks.py.
"""

import frappe

from cabinet_erp.utils.print_logic import print_context

CLIENT_FIELDS = ["client_name", "client_type", "gstin", "state", "phone", "email", "billing_address", "shipping_address"]
PANEL_FIELDS = ["panel_index", "panel_id", "code_name_1", "material_name", "thickness", "finished_length",
	"finished_width", "area", "quantity", "grain", "sheet_index", "pack_group", "edge_band_summary"]


def cabinet_print(doc):
	data = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc)
	company = frappe.get_cached_doc("Cabinet Settings").as_dict()
	client = {}
	if data.get("client"):
		client = frappe.db.get_value("Cabinet Client", data["client"], CLIENT_FIELDS, as_dict=True) or {}

	extra = {}
	if doc.doctype == "Production Order":
		extra["panels"] = frappe.get_all(
			"Order Panel", filters={"production_order": data["name"]}, fields=PANEL_FIELDS, order_by="panel_index asc"
		)
	elif doc.doctype == "Payment Entry Lite" and data.get("invoice"):
		extra["invoice"] = frappe.db.get_value(
			"Cabinet Invoice", data["invoice"], ["posting_date", "rounded_total", "outstanding_amount"], as_dict=True
		)
	elif doc.doctype == "Stock Movement":
		extra["location_title"] = frappe.db.get_value("Stock Location", data.get("location"), "title")
		if data.get("target_location"):
			extra["target_title"] = frappe.db.get_value("Stock Location", data["target_location"], "title")
		# a movement's client = the client the (target) location belongs to
		loc_client = frappe.db.get_value("Stock Location", data.get("target_location") or data.get("location"), "client")
		if loc_client:
			client = frappe.db.get_value("Cabinet Client", loc_client, CLIENT_FIELDS, as_dict=True) or {}

	return print_context(doc.doctype, data, company=company, client=client, extra=extra)


def pdf_url(doctype, name, print_format):
	from urllib.parse import urlencode

	return "/api/method/frappe.utils.print_format.download_pdf?" + urlencode(
		{"doctype": doctype, "name": name, "format": print_format, "no_letterhead": 1}
	)
