"""PDF / print helpers and templates. Plain pytest; the templates are rendered with Jinja2
exactly as Frappe's Print Formats include them."""

import os
import sys

import pytest

from cabinet_erp.billing.billing_logic import compute_invoice
from cabinet_erp.utils.print_logic import (
    FILTERS, fdate, gst_summary, inr, number_in_words, print_context, qty, rupees_in_words,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("value,expected", [
    (0, "0.00"), (999, "999.00"), (1000, "1,000.00"), (104000, "1,04,000.00"), (1234567.5, "12,34,567.50"),
    (123456789, "12,34,56,789.00"), (-11800, "-11,800.00"), (0.005, "0.01"),
])
def test_inr(value, expected):
    assert inr(value) == expected


def test_inr_symbol_and_qty_and_date():
    assert inr(354000, symbol=True) == "₹3,54,000.00"
    assert qty(8.0) == "8" and qty(2.394) == "2.394" and qty(9.0) == "9" and qty(0.746) == "0.746"
    assert fdate("2026-11-03") == "03-11-2026" and fdate(None) == ""


@pytest.mark.parametrize("n,words", [
    (0, "Zero"), (7, "Seven"), (19, "Nineteen"), (40, "Forty"), (115, "One Hundred Fifteen"),
    (1000, "One Thousand"), (104000, "One Lakh Four Thousand"),
    (354000, "Three Lakh Fifty Four Thousand"), (10000000, "One Crore"),
    (2512345678, "Two Hundred Fifty One Crore Twenty Three Lakh Forty Five Thousand Six Hundred Seventy Eight"),
])
def test_number_in_words(n, words):
    assert number_in_words(n) == words


def test_rupees_in_words():
    assert rupees_in_words(354000) == "Rupees Three Lakh Fifty Four Thousand Only"
    assert rupees_in_words(100.5) == "Rupees One Hundred and Fifty Paise Only"
    assert rupees_in_words(-11800) == "Minus Rupees Eleven Thousand Eight Hundred Only"


@pytest.mark.parametrize("inter", [False, True])
def test_gst_summary_matches_invoice_totals(inter):
    items = [{"qty": 1, "rate": 1000, "gst_rate": 18}, {"qty": 3, "rate": 100.01, "gst_rate": "28"},
             {"qty": 1, "rate": 10.01, "gst_rate": 5}, {"qty": 2, "rate": 500, "gst_rate": 18}]
    rows = gst_summary(items, inter)
    totals = compute_invoice(items, "Karnataka", "Maharashtra" if inter else "Karnataka")
    assert [r["rate"] for r in rows] == [5, 18, 28]
    assert round(sum(r["taxable"] for r in rows), 2) == totals["net_total"]
    for k in ("cgst", "sgst", "igst"):
        assert round(sum(r[k] for r in rows), 2) == totals[k]


def test_print_context_titles():
    assert print_context("Cabinet Invoice", {"invoice_type": "Proforma", "items": []})["title"] == "PROFORMA INVOICE"
    assert print_context("Cabinet Invoice", {"invoice_type": "Credit Note", "items": []})["title"] == "CREDIT NOTE"
    assert print_context("Stock Movement", {"movement_type": "Dispatch"})["title"] == "DELIVERY CHALLAN"
    assert print_context("Stock Movement", {"movement_type": "Receipt"})["title"] == "STOCK MOVEMENT"
    p = print_context("Production Order", {}, extra={"panels": [
        {"material_name": "A", "quantity": 2, "area": 500000}, {"material_name": "A", "quantity": 1, "area": 250000}]})
    assert p["panel_total_qty"] == 3 and p["panel_total_area_m2"] == 1.25 and p["panel_groups"] == [{"material": "A", "qty": 3}]


# --- rendering the real templates with the demo data -------------------------

jinja2 = pytest.importorskip("jinja2")
sys.path.insert(0, os.path.join(ROOT, "scripts"))


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    from build_demo_site import build, render_prints
    data = build()
    out = tmp_path_factory.mktemp("print")
    names = render_prints(data, str(out))
    return {n: (out / f"{n}.html").read_text() for n in names}


def test_all_printables_rendered(rendered):
    assert {"INV-26-0001", "INV-26-0002", "INV-26-0003", "PAY-26-0001", "P0001-ORD-01", "SM-26-00006"} <= set(rendered)


def test_intra_state_invoice_pdf(rendered):
    html = rendered["INV-26-0001"]
    assert "TAX INVOICE" in html and "CGST + SGST" in html
    assert "27,000.00" in html and "3,54,000.00" in html and "1,04,000.00" in html
    assert "Rupees Three Lakh Fifty Four Thousand Only" in html
    assert "29AABCD1234E1Z4" in html  # company GSTIN
    assert "IGST (inter-state)" not in html


def test_inter_state_invoice_pdf(rendered):
    html = rendered["INV-26-0002"]
    assert "IGST (inter-state)" in html and "32,400.00" in html and "80,600.00" in html
    assert "Credit notes" in html


def test_credit_note_and_quotation(rendered):
    assert "CREDIT NOTE" in rendered["INV-26-0003"] and "INV-26-0002" in rendered["INV-26-0003"]
    assert "QUOTATION" in rendered["INV-26-0005"] and "valid for 30 days" in rendered["INV-26-0005"]
    assert "Balance due" not in rendered["INV-26-0005"]


def test_receipt_cutlist_challan(rendered):
    assert "PAYMENT RECEIPT" in rendered["PAY-26-0001"] and "One Lakh Fifty Thousand" in rendered["PAY-26-0001"]
    cut = rendered["P0001-ORD-01"]
    assert "PRODUCTION CUTLIST" in cut and "20260911_235002" in cut and cut.count("<tr><td>") >= 88
    ch = rendered["SM-26-00007"]
    assert "DELIVERY CHALLAN" in ch and "Whitefield site is one 18mm sheet short" in ch


def test_print_format_records_point_at_templates():
    import glob
    import json
    for path in glob.glob(os.path.join(ROOT, "cabinet_erp", "*", "print_format", "*", "*.json")):
        d = json.load(open(path))
        assert d["print_format_type"] == "Jinja" and d["standard"] == "Yes" and d["custom_format"] == 1
        tpl = d["html"].split('include "')[1].split('"')[0]
        assert os.path.isfile(os.path.join(ROOT, tpl)), tpl
        assert "cabinet_print(doc)" in d["html"]


def test_filters_registered_in_hooks():
    hooks = open(os.path.join(ROOT, "cabinet_erp", "hooks.py")).read()
    for name in FILTERS:
        assert f"cabinet_erp.utils.print_logic.{name}" in hooks
    assert "cabinet_erp.printing.cabinet_print" in hooks
