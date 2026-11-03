// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cabinet Project", {
	client(frm) {
		if (!frm.doc.client) return;
		frappe.db.get_value("Cabinet Client", frm.doc.client, "client_type").then((r) => {
			if (r.message && r.message.client_type) {
				frm.set_value("project_type", r.message.client_type);
			}
		});
	},
});
