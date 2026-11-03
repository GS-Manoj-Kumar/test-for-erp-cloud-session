// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Movement", {
	setup(frm) {
		const active = { filters: { disabled: 0 } };
		frm.set_query("location", () => active);
		frm.set_query("target_location", () => ({ filters: { disabled: 0, name: ["!=", frm.doc.location || ""] } }));
		frm.set_query("stock_item", "items", () => active);
	},
	refresh(frm) {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__("Ledger"), () => {
				frappe.set_route("List", "Stock Ledger Entry", { movement: frm.doc.name });
			}, __("View"));
		}
	},
});

frappe.ui.form.on("Stock Movement Item", {
	stock_item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.stock_item) return;
		frappe.db.get_value("Stock Item", row.stock_item, "default_rate").then((r) => {
			if (!row.rate && r.message) frappe.model.set_value(cdt, cdn, "rate", r.message.default_rate || 0);
		});
	},
	qty: set_amount,
	rate: set_amount,
});

function set_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}
