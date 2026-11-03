// Copyright (c) 2026, Cabinet ERP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Order", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Download PDF"), () => {
				const args = new URLSearchParams({ doctype: frm.doctype, name: frm.doc.name, format: "Production Cutlist", no_letterhead: 1 });
				window.open(`/api/method/frappe.utils.print_format.download_pdf?${args}`);
			});
		}
		if (frm.is_new()) return;

		if (frm.doc.status !== "Cancelled") {
			frm.add_custom_button(__("Import F4P"), () => import_f4p_dialog(frm));
		}
		frm.add_custom_button(__("Invoice"), () => {
			frappe.new_doc("Cabinet Invoice", {
				client: frm.doc.client,
				project: frm.doc.project,
				production_order: frm.doc.name,
			});
		}, __("Create"));
		frm.add_custom_button(__("Panels"), () => {
			frappe.set_route("List", "Order Panel", { production_order: frm.doc.name });
		}, __("View"));

		if (frm.doc.f4p_warnings) {
			frm.dashboard.set_headline_alert(
				`<div>${__("F4P import warnings")}: ${frappe.utils.escape_html(frm.doc.f4p_warnings)}</div>`,
				"orange"
			);
		}
	},
});

function import_f4p_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Import F4P (sealed f4p.sqlite)"),
		fields: [
			{
				fieldname: "file_url",
				fieldtype: "Attach",
				label: __("f4p.sqlite"),
				reqd: 1,
				options: { restrictions: { allowed_file_types: [".sqlite", ".db"] } },
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"Re-importing the same seal does nothing. A newer seal replaces this order's panels and material lines."
				)}</p>`,
			},
		],
		primary_action_label: __("Import"),
		primary_action(values) {
			frm.call({
				method: "import_f4p",
				doc: frm.doc,
				args: { file_url: values.file_url },
				freeze: true,
				freeze_message: __("Importing F4P..."),
			}).then((r) => {
				d.hide();
				const res = r.message || {};
				if (res.action === "skip") {
					frappe.msgprint(__("Seal {0} is already imported. Nothing changed.", [res.seal_id]));
				} else {
					frappe.show_alert({
						message: __("Imported seal {0}: {1} panels, {2} material lines", [
							res.seal_id, res.panels, res.material_lines,
						]),
						indicator: "green",
					});
				}
				frm.reload_doc();
			});
		},
	});
	d.show();
}
