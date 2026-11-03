// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Project Billing Summary"] = {
	filters: [
		{ fieldname: "client", label: __("Client"), fieldtype: "Link", options: "Cabinet Client" },
		{
			fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Cabinet Project",
			get_query: () => {
				const client = frappe.query_report.get_filter_value("client");
				return client ? { filters: { client } } : {};
			},
		},
		{ fieldname: "from_date", label: __("Invoices From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Invoices To"), fieldtype: "Date" },
	],
};
