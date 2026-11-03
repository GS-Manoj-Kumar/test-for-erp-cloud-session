// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Order Material Status"] = {
	filters: [
		{
			fieldname: "production_order", label: __("Production Order"), fieldtype: "Link",
			options: "Production Order", reqd: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "shortfall" && data && data.shortfall > 0) {
			value = `<span style="color: var(--red-500); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
