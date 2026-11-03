app_name = "cabinet_erp"
app_title = "Cabinet ERP"
app_publisher = "Cabinet ERP"
app_description = "CRM + Inventory + Invoices for a CNC cabinet-production business"
app_email = "admin@example.com"
app_license = "mit"

# Frappe CRM provides CRM Organization / CRM Deal (Contact comes from Frappe core).
required_apps = ["crm"]

# Roles before doctypes sync; General Store location and CRM Deal custom field after.
before_install = "cabinet_erp.install.before_install"
after_install = "cabinet_erp.install.after_install"
before_migrate = "cabinet_erp.install.before_migrate"
after_migrate = "cabinet_erp.install.after_migrate"

# CRM Deal won -> offer to create / link a Cabinet Client.
doc_events = {
	"CRM Deal": {"on_update": "cabinet_erp.clients.crm_glue.on_deal_update"},
}
doctype_js = {"CRM Deal": "public/js/crm_deal.js"}

# Print formats (PDF): {% set p = cabinet_print(doc) %} + templates/print/*.html
jinja = {
	"methods": ["cabinet_erp.printing.cabinet_print"],
	"filters": [
		"cabinet_erp.utils.print_logic.cab_inr",
		"cabinet_erp.utils.print_logic.cab_qty",
		"cabinet_erp.utils.print_logic.cab_date",
	],
}

scheduler_events = {
	"daily": ["cabinet_erp.billing.tasks.mark_overdue"],
}
