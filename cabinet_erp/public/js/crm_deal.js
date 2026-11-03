// Desk form for CRM Deal: create / open the linked Cabinet Client.
frappe.ui.form.on("CRM Deal", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.cabinet_client) {
			frm.add_custom_button(__("Cabinet Client"), () => frappe.set_route("Form", "Cabinet Client", frm.doc.cabinet_client), __("View"));
		} else if (frm.doc.status === "Won") {
			frm.add_custom_button(__("Create Cabinet Client"), () => {
				frappe.call({
					method: "cabinet_erp.clients.crm_glue.make_client_from_deal",
					args: { deal: frm.doc.name },
				}).then((r) => {
					frm.reload_doc();
					if (r.message) frappe.set_route("Form", "Cabinet Client", r.message);
				});
			}).addClass("btn-primary");
		}
	},
});
