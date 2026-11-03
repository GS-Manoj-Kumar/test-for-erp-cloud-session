# Copyright (c) 2026, Cabinet ERP and contributors
# Bench-only integration test (runs with `bench run-tests`, not plain pytest).

import frappe
from frappe.tests.utils import FrappeTestCase

from cabinet_erp.inventory.doctype.stock_location.stock_location import get_or_create_location
from cabinet_erp.inventory.doctype.stock_movement.stock_movement import get_balance


def make_movement(mtype, location, qty, item, submit=True, **kw):
	doc = frappe.get_doc(
		{
			"doctype": "Stock Movement",
			"movement_type": mtype,
			"location": location,
			"items": [{"stock_item": item, "qty": qty, "rate": 100}],
			**kw,
		}
	).insert()
	if submit:
		doc.submit()
	return doc


class TestStockMovement(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Stock Item", "TEST-CORE-18"):
			frappe.get_doc(
				{"doctype": "Stock Item", "item_code": "TEST-CORE-18", "item_name": "18mm core", "kind": "Core Sheet", "uom": "Sheet"}
			).insert()
		self.item = "TEST-CORE-18"
		client = frappe.get_doc({"doctype": "Cabinet Client", "client_name": "Stock Test", "client_type": "B2C"}).insert()
		self.p1 = frappe.get_doc({"doctype": "Cabinet Project", "client": client.name, "project_name": "A"}).insert()
		self.p2 = frappe.get_doc({"doctype": "Cabinet Project", "client": client.name, "project_name": "B"}).insert()
		self.loc1 = get_or_create_location("Project", self.p1.name)
		self.loc2 = get_or_create_location("Project", self.p2.name)

	def test_receipt_issue_cancel(self):
		make_movement("Receipt", self.loc1, 5, self.item)
		issue = make_movement("Issue to Production", self.loc1, 3, self.item)
		self.assertEqual(get_balance(self.loc1, "Received", self.item), 2)
		self.assertEqual(get_balance(self.loc1, "In Process", self.item), 3)
		self.assertRaises(frappe.ValidationError, make_movement, "Issue to Production", self.loc1, 3, self.item)
		issue.cancel()
		self.assertEqual(get_balance(self.loc1, "Received", self.item), 5)
		rows = frappe.db.count("Stock Ledger Entry", {"movement": issue.name})
		self.assertEqual(rows, 4)  # 2 original + 2 reversing, nothing deleted

	def test_project_transfer_needs_urgent(self):
		make_movement("Receipt", self.loc1, 5, self.item)
		self.assertRaises(
			frappe.ValidationError, make_movement, "Transfer", self.loc1, 2, self.item, target_location=self.loc2
		)
		t = make_movement(
			"Transfer", self.loc1, 2, self.item, target_location=self.loc2, is_urgent=1, reason="Site waiting"
		)
		self.assertEqual(t.approver, frappe.session.user)
		self.assertEqual(get_balance(self.loc2, "Received", self.item), 2)
