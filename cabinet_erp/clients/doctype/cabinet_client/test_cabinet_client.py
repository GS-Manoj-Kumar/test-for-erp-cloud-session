# Copyright (c) 2026, Cabinet ERP and contributors
# Bench-only integration test (runs with `bench run-tests`, not plain pytest).

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCabinetClient(FrappeTestCase):
	def test_naming_and_gstin(self):
		doc = frappe.get_doc(
			{"doctype": "Cabinet Client", "client_name": "Test B2B", "client_type": "B2B", "gstin": "27aapfu0939f1zv"}
		).insert()
		self.assertRegex(doc.name, r"^C\d{4}$")
		self.assertEqual(doc.gstin, "27AAPFU0939F1ZV")
		self.assertEqual(doc.state, "Maharashtra")

	def test_bad_gstin_rejected(self):
		doc = frappe.get_doc(
			{"doctype": "Cabinet Client", "client_name": "Bad", "client_type": "B2B", "gstin": "27AAPFU0939F1ZX"}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)
