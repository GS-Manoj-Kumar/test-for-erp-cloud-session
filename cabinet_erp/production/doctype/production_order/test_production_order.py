# Copyright (c) 2026, Cabinet ERP and contributors
# Bench-only integration test (runs with `bench run-tests`, not plain pytest).

import os

import frappe
from frappe.tests.utils import FrappeTestCase

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tests", "fixtures", "f4p.sqlite")


class TestProductionOrder(FrappeTestCase):
	def test_naming_and_import(self):
		client = frappe.get_doc({"doctype": "Cabinet Client", "client_name": "PO Test", "client_type": "B2C"}).insert()
		project = frappe.get_doc({"doctype": "Cabinet Project", "client": client.name, "project_name": "Kitchen"}).insert()
		order = frappe.get_doc({"doctype": "Production Order", "project": project.name}).insert()
		self.assertEqual(order.name, f"{project.name}-ORD-01")
		self.assertEqual(order.client, client.name)

		with open(FIXTURE, "rb") as f:
			file_doc = frappe.get_doc(
				{"doctype": "File", "file_name": "f4p.sqlite", "content": f.read(), "is_private": 1}
			).insert()

		res = order.import_f4p(file_doc.file_url)
		self.assertEqual(res["action"], "new")
		self.assertEqual(frappe.db.count("Order Panel", {"production_order": order.name}), 88)
		self.assertEqual(len(order.material_lines), 12)

		res = order.import_f4p(file_doc.file_url)
		self.assertEqual(res["action"], "skip")
		self.assertEqual(frappe.db.count("Order Panel", {"production_order": order.name}), 88)
