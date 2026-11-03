// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cabinet Invoice", {
	setup(frm) {
		frm.set_query("project", () => (frm.doc.client ? { filters: { client: frm.doc.client } } : {}));
		frm.set_query("production_order", () => {
			if (frm.doc.project) return { filters: { project: frm.doc.project } };
			return frm.doc.client ? { filters: { client: frm.doc.client } } : {};
		});
		frm.set_query("return_against", () => ({
			filters: { client: frm.doc.client, docstatus: 1, invoice_type: "Tax Invoice" },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.production_order) {
			frm.add_custom_button(__("Make from Order"), () => make_from_order(frm));
		}
		if (frm.doc.docstatus === 1 && frm.doc.invoice_type === "Tax Invoice") {
			if (flt(frm.doc.outstanding_amount) > 0) {
				frm.add_custom_button(__("Payment"), () => {
					frappe.new_doc("Payment Entry Lite", {
						client: frm.doc.client,
						invoice: frm.doc.name,
						amount: frm.doc.outstanding_amount,
					});
				}, __("Create"));
				frm.add_custom_button(__("Credit Note"), () => {
					frappe.new_doc("Cabinet Invoice", {
						invoice_type: "Credit Note",
						client: frm.doc.client,
						project: frm.doc.project,
						production_order: frm.doc.production_order,
						place_of_supply: frm.doc.place_of_supply,
						return_against: frm.doc.name,
					});
				}, __("Create"));
			}
			frm.add_custom_button(__("Payments"), () => {
				frappe.set_route("List", "Payment Entry Lite", { invoice: frm.doc.name });
			}, __("View"));
		}
	},
	client(frm) {
		if (!frm.doc.client) return;
		frappe.db.get_value("Cabinet Client", frm.doc.client, "state").then((r) => {
			if (r.message && r.message.state) frm.set_value("place_of_supply", r.message.state);
		});
	},
	production_order(frm) {
		if (!frm.doc.production_order) return;
		frappe.db.get_value("Production Order", frm.doc.production_order, ["project", "client"]).then((r) => {
			const v = r.message || {};
			if (v.client && !frm.doc.client) frm.set_value("client", v.client);
			if (v.project) frm.set_value("project", v.project);
		});
	},
});

frappe.ui.form.on("Cabinet Invoice Item", {
	qty: set_amount,
	rate: set_amount,
});

function set_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
}

function make_from_order(frm) {
	frappe.prompt(
		[
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("Fill items from"),
				options: [
					{ value: "lines", label: __("Material lines (one row each)") },
					{ value: "lump_sum", label: __("Single lump-sum line (order cost)") },
				],
				default: "lines",
				reqd: 1,
			},
			{ fieldname: "replace", fieldtype: "Check", label: __("Replace existing items"), default: 1 },
		],
		(values) => {
			frappe.call({
				method: "cabinet_erp.billing.doctype.cabinet_invoice.cabinet_invoice.get_order_items",
				args: { production_order: frm.doc.production_order, mode: values.mode },
			}).then((r) => {
				if (values.replace) frm.clear_table("items");
				(r.message || []).forEach((row) => frm.add_child("items", row));
				frm.refresh_field("items");
				frm.dirty();
				frappe.show_alert({ message: __("Added {0} item(s). Save to calculate GST.", [(r.message || []).length]), indicator: "green" });
			});
		},
		__("Make from Order"),
		__("Fill")
	);
}
