import frappe

ROLES = ("Cabinet Admin", "Sales", "Production", "Accounts")


def before_install():
	ensure_roles()


def before_migrate():
	ensure_roles()


def after_install():
	after_migrate()


def after_migrate():
	ensure_roles()
	ensure_general_location()
	ensure_crm_fields()


def ensure_roles():
	"""Roles must exist before doctype permissions that use them are synced."""
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	frappe.db.commit()


def ensure_general_location():
	if not frappe.db.exists("DocType", "Stock Location"):
		return
	if not frappe.db.exists("Stock Location", {"scope": "General"}):
		frappe.get_doc({"doctype": "Stock Location", "scope": "General"}).insert(ignore_permissions=True)
		frappe.db.commit()


def ensure_crm_fields():
	"""CRM Deal.cabinet_client: which Cabinet Client a won deal became."""
	if not frappe.db.exists("DocType", "CRM Deal"):
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"CRM Deal": [
				{
					"fieldname": "cabinet_client",
					"label": "Cabinet Client",
					"fieldtype": "Link",
					"options": "Cabinet Client",
					"insert_after": "organization",
					"read_only": 1,
					"no_copy": 1,
				}
			]
		},
		update=True,
	)
