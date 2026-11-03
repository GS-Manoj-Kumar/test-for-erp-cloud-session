"""Load the dummy demo data (cabinet_erp/demo_data.py) into a site, through the real
controllers (validation, F4P import, stock ledger, GST, payments).

    bench --site <site> execute cabinet_erp.demo.setup_demo

Meant for a fresh site (the Codespaces live preview). It refuses to run if the site
already has Cabinet Clients, unless called with force=1.
"""

import os

import frappe

from cabinet_erp import demo_data as D
from cabinet_erp.inventory.doctype.stock_location.stock_location import get_or_create_location


def setup_demo(force=0):
	if frappe.db.count("Cabinet Client") and not int(force):
		print("Site already has Cabinet Clients; not loading demo data (pass force=1 to load anyway).")
		return

	names = {}  # demo key -> real document name

	settings = frappe.get_single("Cabinet Settings")
	settings.update(D.COMPANY)
	settings.save()

	for c in D.CLIENTS:
		doc = frappe.get_doc({"doctype": "Cabinet Client", **_without_key(c)}).insert()
		names[c["key"]] = doc.name

	for p in D.PROJECTS:
		doc = frappe.get_doc({"doctype": "Cabinet Project", **_without_key(p), "client": names[p["client"]]}).insert()
		names[p["key"]] = doc.name

	for i in D.STOCK_ITEMS:
		if not frappe.db.exists("Stock Item", i["item_code"]):
			frappe.get_doc({"doctype": "Stock Item", **i}).insert()

	for o in D.ORDERS:
		doc = frappe.get_doc(
			{
				"doctype": "Production Order",
				"project": names[o["project"]],
				"order_title": o["order_title"],
				"status": o["status"],
			}
		).insert()
		names[o["key"]] = doc.name
		if o.get("import_fixture"):
			doc.import_f4p(_fixture_file_url())
			doc.reload()
			lines = [d.as_dict() for d in doc.material_lines]
		else:
			lines = o.get("material_lines") or []
		priced = D.priced_lines([{k: l.get(k) for k in ("kind", "description", "size", "qty", "order_qty", "wastage_pct")} for l in lines])
		doc.set("material_lines", priced)
		doc.update(D.line_costs(priced) if priced else {})
		doc.save()

	names[D.GENERAL] = get_or_create_location("General")
	for loc in D.LOCATIONS:
		link = loc.get("project") or loc.get("production_order") or loc.get("client")
		names[loc["key"]] = get_or_create_location(loc["scope"], names[link])

	for m in D.MOVEMENTS:
		doc = frappe.get_doc(
			{
				"doctype": "Stock Movement",
				**_without_key(m),
				"location": names[m["location"]],
				"target_location": names.get(m.get("target_location")),
				"items": [dict(i) for i in m["items"]],
			}
		).insert()
		doc.submit()

	for i in D.INVOICES:
		doc = frappe.get_doc(
			{
				"doctype": "Cabinet Invoice",
				**_without_key(i),
				"client": names[i["client"]],
				"project": names.get(i.get("project")),
				"production_order": names.get(i.get("production_order")),
				"return_against": names.get(i.get("return_against")),
				"items": [dict(r) for r in i["items"]],
			}
		).insert()
		doc.submit()
		names[i["key"]] = doc.name

	for p in D.PAYMENTS:
		frappe.get_doc(
			{
				"doctype": "Payment Entry Lite",
				**_without_key(p),
				"client": names[p["client"]],
				"invoice": names[p["invoice"]],
			}
		).insert().submit()

	frappe.db.commit()
	print(f"Demo data loaded: {len(D.CLIENTS)} clients, {len(D.PROJECTS)} projects, {len(D.ORDERS)} orders, "
	      f"{len(D.MOVEMENTS)} stock movements, {len(D.INVOICES)} invoices, {len(D.PAYMENTS)} payments.")


def _without_key(d):
	return {k: v for k, v in d.items() if k != "key"}


def _fixture_file_url():
	path = os.path.join(frappe.get_app_path("cabinet_erp"), "..", "tests", "fixtures", "f4p.sqlite")
	with open(path, "rb") as f:
		content = f.read()
	file_doc = frappe.get_doc(
		{"doctype": "File", "file_name": "f4p.sqlite", "content": content, "is_private": 1}
	).insert(ignore_permissions=True)
	return file_doc.file_url
