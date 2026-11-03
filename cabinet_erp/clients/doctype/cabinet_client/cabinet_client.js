// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cabinet Client", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Projects"), () => {
				frappe.set_route("List", "Cabinet Project", { client: frm.doc.name });
			}, __("View"));
			frm.add_custom_button(__("New Project"), () => {
				frappe.new_doc("Cabinet Project", { client: frm.doc.name });
			}, __("Create"));
		}
	},
	gstin(frm) {
		if (frm.doc.gstin) frm.set_value("gstin", frm.doc.gstin.trim().toUpperCase());
	},
});
