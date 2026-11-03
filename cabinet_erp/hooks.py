app_name = "cabinet_erp"
app_title = "Cabinet ERP"
app_publisher = "Cabinet ERP"
app_description = "CRM + Inventory + Invoices for a CNC cabinet-production business"
app_email = "admin@example.com"
app_license = "mit"

# Frappe CRM provides CRM Organization / CRM Deal (Contact comes from Frappe core).
required_apps = ["crm"]

# Make sure the default "General Store" Stock Location exists.
after_install = "cabinet_erp.install.after_install"
after_migrate = "cabinet_erp.install.after_migrate"

# Phase 5 will add: doc_events for "CRM Deal" (Won -> Cabinet Client),
# fixtures for roles, and the workspace.

scheduler_events = {
	"daily": ["cabinet_erp.billing.tasks.mark_overdue"],
}
