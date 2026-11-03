"""The demo dataset must stay valid against the app's rules (the build script raises if a
movement, payment or credit note would be rejected)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_demo_site import build  # noqa: E402

from cabinet_erp import demo_data as D  # noqa: E402
from cabinet_erp.utils.gst import gstin_error  # noqa: E402


def test_demo_builds():
    data = build()
    docs = data["docs"]
    assert len(docs["Order Panel"]) == 88
    assert len(docs["Stock Ledger Entry"]) > 0
    inv = {i["name"]: i for i in docs["Cabinet Invoice"]}
    assert inv["INV-26-0001"]["cgst"] == inv["INV-26-0001"]["sgst"] == 27000     # Karnataka -> Karnataka
    assert inv["INV-26-0002"]["igst"] == 32400                                    # Karnataka -> Maharashtra
    assert inv["INV-26-0002"]["outstanding_amount"] == 212400 - 11800 - 120000
    assert inv["INV-26-0003"]["status"] == "Issued"
    assert inv["INV-26-0006"]["status"] == "Unpaid"
    shortfalls = [r for r in data["reports"]["Order Material Status"]["P0001-ORD-01"] if r["shortfall"] > 0]
    assert [r["stock_item"] for r in shortfalls] == ["EB-10"]


def test_demo_gstins_valid():
    for g in [D.COMPANY["company_gstin"]] + [c["gstin"] for c in D.CLIENTS if c.get("gstin")]:
        assert gstin_error(g) is None, g


def test_every_fixture_line_maps_to_a_stock_item():
    from cabinet_erp.production.f4p_import import parse_f4p
    lines = parse_f4p(os.path.join(ROOT, "tests", "fixtures", "f4p.sqlite"))["material_lines"]
    assert all(D.stock_item_for_line(l["kind"], l["description"]) for l in lines)
