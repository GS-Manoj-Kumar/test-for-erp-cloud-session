"""GST, outstanding, status and report helpers for Billing. Plain pytest, no bench."""

import datetime as dt

import pytest

from cabinet_erp.billing.billing_logic import (
    CREDIT_NOTE, PROFORMA, QUOTATION, TAX_INVOICE,
    BillingError, ageing_bucket, ageing_row, compute_invoice, credit_note_errors,
    invoice_status, is_inter_state, order_invoice_items, outstanding, payment_errors,
    project_summary,
)

KA, MH = "Karnataka", "Maharashtra"


def it(qty, rate, gst=18):
    return {"qty": qty, "rate": rate, "gst_rate": gst}


# --- GST --------------------------------------------------------------------

def test_intra_state_splits_cgst_sgst():
    r = compute_invoice([it(2, 50000)], KA, KA)
    assert r["is_inter_state"] == 0
    assert r["net_total"] == 100000
    assert r["cgst"] == r["sgst"] == 9000
    assert r["igst"] == 0
    assert r["grand_total"] == r["rounded_total"] == 118000


def test_inter_state_uses_igst():
    r = compute_invoice([it(2, 50000)], KA, MH)
    assert r["is_inter_state"] == 1
    assert r["igst"] == 18000 and r["cgst"] == r["sgst"] == 0
    assert r["rounded_total"] == 118000


def test_mixed_rates_grouped():
    r = compute_invoice([it(1, 1000, 18), it(1, 1000, 18), it(3, 100, 28), it(1, 500, 0), it(1, 200, 5)], KA, KA)
    assert r["amounts"] == [1000, 1000, 300, 500, 200]
    assert r["net_total"] == 3000
    # 18% on 2000 = 360, 28% on 300 = 84, 5% on 200 = 10 -> 454 total
    assert r["cgst"] == r["sgst"] == 227
    assert r["total_tax"] == 454


def test_cgst_equals_sgst_with_odd_paise():
    r = compute_invoice([it(1, 10.01, 5)], KA, KA)   # 5% of 10.01 = 0.5005
    assert r["cgst"] == r["sgst"] == 0.25
    assert r["total_tax"] == 0.50


def test_rounding_to_rupee():
    r = compute_invoice([it(1, 100.42, 0)], KA, KA)
    assert r["rounded_total"] == 100 and r["rounding_adjustment"] == -0.42
    r = compute_invoice([it(1, 100.50, 0)], KA, KA)
    assert r["rounded_total"] == 101 and r["rounding_adjustment"] == 0.5   # half rounds up


def test_line_amount_rounded_to_paise():
    r = compute_invoice([it(3, 33.333, 0)], KA, KA)
    assert r["amounts"] == [100.0]


def test_float_safety():
    r = compute_invoice([it(1, 0.1, 0), it(1, 0.2, 0)], KA, KA)
    assert r["net_total"] == 0.3


def test_invalid_gst_rate():
    with pytest.raises(BillingError, match="GST rate 15"):
        compute_invoice([it(1, 100, 15)], KA, KA)


def test_gst_rate_as_string_from_select_field():
    r = compute_invoice([{"qty": 1, "rate": 100, "gst_rate": "12"}], KA, MH)
    assert r["igst"] == 12


def test_is_inter_state():
    assert is_inter_state(KA, MH)
    assert not is_inter_state(KA, KA)
    assert not is_inter_state(KA, None)   # unknown place of supply -> treat as local


# --- outstanding & status ---------------------------------------------------

TODAY = dt.date(2026, 11, 3)


def test_outstanding():
    assert outstanding(118000) == 118000
    assert outstanding(118000, 50000) == 68000
    assert outstanding(118000, 50000, 18000) == 50000
    assert outstanding(100.1, 0.1) == 100.0


@pytest.mark.parametrize("paid,credited,due,expected", [
    (0, 0, "2026-11-30", "Unpaid"),
    (100, 0, "2026-11-30", "Partly Paid"),
    (0, 100, "2026-11-30", "Partly Paid"),
    (1000, 0, "2026-11-30", "Paid"),
    (600, 400, "2026-11-30", "Paid"),
    (0, 0, "2026-11-02", "Overdue"),
    (500, 0, "2026-11-02", "Overdue"),
    (1000, 0, "2026-10-01", "Paid"),        # paid beats overdue
    (0, 0, "2026-11-03", "Unpaid"),         # due today is not overdue
    (0, 0, None, "Unpaid"),
])
def test_tax_invoice_status(paid, credited, due, expected):
    assert invoice_status(1, TAX_INVOICE, 1000, paid, credited, due, TODAY) == expected


def test_status_draft_cancelled_issued():
    assert invoice_status(0, TAX_INVOICE, 1000) == "Draft"
    assert invoice_status(2, TAX_INVOICE, 1000) == "Cancelled"
    for t in (QUOTATION, PROFORMA, CREDIT_NOTE):
        assert invoice_status(1, t, 1000, due_date="2020-01-01", today=TODAY) == "Issued"


# --- payments & credit notes ------------------------------------------------

def test_payment_ok():
    assert payment_errors(500, 1000, client="C0001", invoice_client="C0001") == []
    assert payment_errors(1000, 1000) == []


@pytest.mark.parametrize("kwargs,msg", [
    ({"amount": 0, "invoice_outstanding": 1000}, "greater than 0"),
    ({"amount": -5, "invoice_outstanding": 1000}, "greater than 0"),
    ({"amount": 1000.01, "invoice_outstanding": 1000}, "more than the outstanding"),
    ({"amount": 10, "invoice_outstanding": 1000, "invoice_docstatus": 0}, "submitted"),
    ({"amount": 10, "invoice_outstanding": 1000, "invoice_type": PROFORMA}, "Only a Tax Invoice"),
    ({"amount": 10, "invoice_outstanding": 1000, "invoice_client": "C0001", "client": "C0002"}, "belongs to client"),
])
def test_payment_errors(kwargs, msg):
    assert any(msg in e for e in payment_errors(**kwargs))


def test_credit_note_rules():
    assert credit_note_errors(500, 1000, TAX_INVOICE, 1) == []
    assert any("more than" in e for e in credit_note_errors(1500, 1000, TAX_INVOICE, 1))
    assert any("submitted Tax Invoice" in e for e in credit_note_errors(10, 1000, PROFORMA, 1))
    assert any("submitted Tax Invoice" in e for e in credit_note_errors(10, 1000, TAX_INVOICE, 0))
    assert any("belongs to client" in e for e in credit_note_errors(10, 1000, TAX_INVOICE, 1, "C1", "C2"))


def test_payment_then_credit_then_payment_flow():
    total = compute_invoice([it(1, 10000)], KA, KA)["rounded_total"]     # 11800
    paid, credited = 5000, 0
    assert invoice_status(1, TAX_INVOICE, total, paid, credited, "2026-12-01", TODAY) == "Partly Paid"
    assert credit_note_errors(1800, outstanding(total, paid, credited), TAX_INVOICE, 1) == []
    credited = 1800
    remaining = outstanding(total, paid, credited)
    assert remaining == 5000
    assert payment_errors(5000.01, remaining)                            # overpay blocked
    paid += remaining
    assert invoice_status(1, TAX_INVOICE, total, paid, credited, "2026-12-01", TODAY) == "Paid"


# --- Make from Order --------------------------------------------------------

ORDER = {"name": "P0001-ORD-01", "order_title": "Kitchen", "cost_grand": 45678.456}
LINES = [
    {"kind": "core", "description": "18.0mm", "size": "8X4", "qty": 7, "order_qty": 8, "unit_price": 2450},
    {"kind": "edge_band", "description": "C4_1.0mm 2.28m", "size": "", "qty": 2.28, "order_qty": 2.394, "unit_price": 0},
]


def test_items_from_material_lines():
    rows = order_invoice_items(ORDER, LINES, "lines", gst_rate=18)
    assert rows[0] == {"description": "Core 18.0mm 8X4", "qty": 8.0, "uom": "Sheet", "rate": 2450.0, "gst_rate": 18}
    assert rows[1]["uom"] == "m" and rows[1]["qty"] == 2.394
    assert rows[1]["description"] == "Edge band C4_1.0mm 2.28m"


def test_items_lump_sum():
    rows = order_invoice_items(ORDER, LINES, "lump_sum", gst_rate=12)
    assert rows == [{"description": "Production order P0001-ORD-01 - Kitchen", "qty": 1, "uom": "Nos",
                     "rate": 45678.46, "gst_rate": 12}]


def test_items_bad_mode():
    with pytest.raises(BillingError):
        order_invoice_items(ORDER, LINES, "everything")


# --- reports ----------------------------------------------------------------

@pytest.mark.parametrize("days,bucket", [(0, "0-30"), (30, "0-30"), (31, "31-60"), (60, "31-60"),
                                         (61, "61-90"), (90, "61-90"), (91, "90+"), (400, "90+")])
def test_ageing_bucket(days, bucket):
    assert ageing_bucket(days) == bucket


def test_ageing_row():
    row = ageing_row({"name": "INV-1", "due_date": "2026-09-01", "posting_date": "2026-08-15",
                      "outstanding_amount": 2500}, "2026-11-03")
    assert row["days_overdue"] == 63
    assert row["b_61_90"] == 2500 and row["b_0_30"] == row["b_31_60"] == row["b_90_plus"] == 0
    not_due = ageing_row({"due_date": "2026-12-01", "outstanding_amount": 10}, "2026-11-03")
    assert not_due["days_overdue"] == 0 and not_due["b_0_30"] == 10
    no_due = ageing_row({"due_date": None, "posting_date": "2026-07-01", "outstanding_amount": 1}, "2026-11-03")
    assert no_due["b_90_plus"] == 1


def test_project_summary():
    invoices = [
        {"project": "P0001", "invoice_type": TAX_INVOICE, "net_total": 100000, "rounded_total": 118000,
         "paid_amount": 50000, "outstanding_amount": 56200},
        {"project": "P0001", "invoice_type": CREDIT_NOTE, "net_total": 10000, "rounded_total": 11800,
         "paid_amount": 0, "outstanding_amount": 0},
        {"project": None, "invoice_type": TAX_INVOICE, "net_total": 5, "rounded_total": 5,
         "paid_amount": 0, "outstanding_amount": 5},
    ]
    out = project_summary(invoices, {"P0001": 60000, "P0002": 1000})
    p1, p2 = out
    assert p1["invoiced"] == 106200 and p1["invoiced_net"] == 90000
    assert p1["paid"] == 50000 and p1["outstanding"] == 56200
    assert p1["margin"] == 30000 and p1["margin_pct"] == 33.33
    assert p2 == {"project": "P0002", "invoiced": 0, "invoiced_net": 0, "paid": 0, "outstanding": 0,
                  "order_cost": 1000, "margin": -1000, "margin_pct": 0}
