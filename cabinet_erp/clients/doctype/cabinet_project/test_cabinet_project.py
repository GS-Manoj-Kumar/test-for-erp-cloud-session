# Copyright (c) 2026, Cabinet ERP and contributors
# Bench-only integration test (runs with `bench run-tests`, not plain pytest).

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCabinetProject(FrappeTestCase):
	def test_naming_and_type_default(self):
		client = frappe.get_doc({"doctype": "Cabinet Client", "client_name": "Proj Test", "client_type": "B2B"}).insert()
		project = frappe.get_doc(
			{"doctype": "Cabinet Project", "client": client.name, "project_name": "Office Fitout"}
		).insert()
		self.assertRegex(project.name, r"^P\d{4}$")
		self.assertEqual(project.project_type, "B2B")
		self.assertEqual(project.milestone, "Enquiry")
