// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	filters: [
		{ fieldname: "to_date", label: __("As On"), fieldtype: "Date", default: frappe.datetime.get_today() },
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
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Stock Location" },
		{ fieldname: "stock_item", label: __("Stock Item"), fieldtype: "Link", options: "Stock Item" },
		{ fieldname: "state", label: __("State"), fieldtype: "Select", options: "\nReceived\nIn Process\nSent" },
	],
};
