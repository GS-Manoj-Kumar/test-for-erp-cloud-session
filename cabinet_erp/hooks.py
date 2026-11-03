app_name = "cabinet_erp"
app_title = "Cabinet ERP"
app_publisher = "Cabinet ERP"
app_description = "CRM + Inventory + Invoices for a CNC cabinet-production business"
app_email = "admin@example.com"
app_license = "mit"

# Frappe CRM provides CRM Organization / CRM Deal (Contact comes from Frappe core).
required_apps = ["crm"]

# Phase 5 will add: doc_events for "CRM Deal" (Won -> Cabinet Client),
# fixtures for roles, and the workspace.
# Phase 4 will add: scheduler_events for the daily Overdue invoice check.
