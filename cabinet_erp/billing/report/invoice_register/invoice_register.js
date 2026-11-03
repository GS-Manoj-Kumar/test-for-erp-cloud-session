// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Invoice Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "client", label: __("Client"), fieldtype: "Link", options: "Cabinet Client" },
		{
			fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Cabinet Project",
			get_query: () => {
				const client = frappe.query_report.get_filter_value("client");
				return client ? { filters: { client } } : {};
			},
		},
		{
			fieldname: "production_order", label: __("Order"), fieldtype: "Link", options: "Production Order",
			get_query: () => {
				const project = frappe.query_report.get_filter_value("project");
				return project ? { filters: { project } } : {};
			},
		},
		{
			fieldname: "status", label: __("Status"), fieldtype: "Select",
			options: "\nDraft\nIssued\nUnpaid\nPartly Paid\nPaid\nOverdue\nCancelled",
		},
		{
			fieldname: "invoice_type", label: __("Invoice Type"), fieldtype: "Select",
			options: "\nQuotation\nProforma\nTax Invoice\nCredit Note",
		},
	],
};
