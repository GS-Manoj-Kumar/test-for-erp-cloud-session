// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Entry Lite", {
	setup(frm) {
		frm.set_query("invoice", () => ({
			filters: {
				docstatus: 1,
				invoice_type: "Tax Invoice",
				outstanding_amount: [">", 0],
				...(frm.doc.client ? { client: frm.doc.client } : {}),
			},
		}));
	},
	invoice(frm) {
		if (!frm.doc.invoice) return;
		frappe.db.get_value("Cabinet Invoice", frm.doc.invoice, ["client", "outstanding_amount"]).then((r) => {
			const v = r.message || {};
			if (v.client) frm.set_value("client", v.client);
			if (!frm.doc.amount) frm.set_value("amount", v.outstanding_amount);
		});
	},
});
