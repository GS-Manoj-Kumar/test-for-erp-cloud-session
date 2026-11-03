# Copyright (c) 2026, Cabinet ERP and contributors
# Bench-only integration test (runs with `bench run-tests`, not plain pytest).

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate


class TestCabinetInvoice(FrappeTestCase):
	def setUp(self):
		settings = frappe.get_single("Cabinet Settings")
		settings.company_state = "Karnataka"
		settings.default_due_days = 15
		settings.save()
		self.client_ka = frappe.get_doc(
			{"doctype": "Cabinet Client", "client_name": "Local", "client_type": "B2C", "state": "Karnataka"}
		).insert()
		self.client_mh = frappe.get_doc(
			{"doctype": "Cabinet Client", "client_name": "Remote", "client_type": "B2C", "state": "Maharashtra"}
		).insert()

	def invoice(self, client, rate=10000, **kw):
		return frappe.get_doc(
			{
				"doctype": "Cabinet Invoice",
				"client": client.name,
				"items": [{"description": "Kitchen", "qty": 1, "rate": rate, "gst_rate": "18"}],
				**kw,
			}
		).insert()

	def pay(self, inv, amount):
		return frappe.get_doc(
			{"doctype": "Payment Entry Lite", "client": inv.client, "invoice": inv.name, "amount": amount, "mode": "Cash"}
		).insert()

	def test_gst_split(self):
		local = self.invoice(self.client_ka)
		self.assertEqual((local.cgst, local.sgst, local.igst), (900, 900, 0))
		remote = self.invoice(self.client_mh)
		self.assertEqual((remote.cgst, remote.sgst, remote.igst), (0, 0, 1800))
		self.assertEqual(remote.due_date, add_days(nowdate(), 15))

	def test_payments_and_status(self):
		inv = self.invoice(self.client_ka)
		inv.submit()
		inv.reload()
		self.assertEqual((inv.status, inv.outstanding_amount), ("Unpaid", 11800))
		p = self.pay(inv, 5000)
		p.submit()
		inv.reload()
		self.assertEqual((inv.status, inv.paid_amount, inv.outstanding_amount), ("Partly Paid", 5000, 6800))
		self.assertRaises(frappe.ValidationError, self.pay, inv, 7000)
		p.cancel()
		inv.reload()
		self.assertEqual((inv.status, inv.outstanding_amount), ("Unpaid", 11800))

	def test_credit_note(self):
		inv = self.invoice(self.client_ka)
		inv.submit()
		cn = self.invoice(self.client_ka, rate=1000, invoice_type="Credit Note", return_against=inv.name)
		cn.submit()
		inv.reload()
		self.assertEqual((inv.credited_amount, inv.outstanding_amount, inv.status), (1180, 10620, "Partly Paid"))
		self.assertEqual(frappe.db.get_value("Cabinet Invoice", cn.name, "status"), "Issued")

	def test_pdf_print_format(self):
		inv = self.invoice(self.client_mh)
		inv.submit()
		html = frappe.get_print("Cabinet Invoice", inv.name, print_format="Cabinet Tax Invoice")
		self.assertIn("TAX INVOICE", html)
		self.assertIn("IGST (inter-state)", html)
		self.assertIn("Rupees Eleven Thousand Eight Hundred Only", html)
		pdf = frappe.get_print("Cabinet Invoice", inv.name, print_format="Cabinet Tax Invoice", as_pdf=True)
		self.assertTrue(pdf.startswith(b"%PDF"))
