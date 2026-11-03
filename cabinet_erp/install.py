import frappe


def after_install():
	ensure_general_location()


def after_migrate():
	ensure_general_location()


def ensure_general_location():
	if not frappe.db.exists("DocType", "Stock Location"):
		return
	if not frappe.db.exists("Stock Location", {"scope": "General"}):
		frappe.get_doc({"doctype": "Stock Location", "scope": "General"}).insert(ignore_permissions=True)
		frappe.db.commit()
