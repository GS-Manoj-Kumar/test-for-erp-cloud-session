// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Location", {
	setup(frm) {
		frm.set_query("project", () => (frm.doc.client ? { filters: { client: frm.doc.client } } : {}));
	},
});
