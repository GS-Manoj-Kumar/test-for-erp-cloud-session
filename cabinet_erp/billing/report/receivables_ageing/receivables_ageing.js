// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Receivables Ageing"] = {
	filters: [
		{ fieldname: "as_of", label: __("As Of"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "client", label: __("Client"), fieldtype: "Link", options: "Cabinet Client" },
		{
			fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Cabinet Project",
			get_query: () => {
				const client = frappe.query_report.get_filter_value("client");
				return client ? { filters: { client } } : {};
			},
		},
	],
};
