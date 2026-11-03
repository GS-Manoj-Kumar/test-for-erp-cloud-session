"""Static checks on every doctype JSON. Runs with plain pytest, no bench."""

import glob
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "cabinet_erp")
DOCTYPE_FILES = sorted(glob.glob(os.path.join(APP, "*", "doctype", "*", "*.json")))

MODULES = [m.strip() for m in open(os.path.join(APP, "modules.txt")) if m.strip()]

# Doctypes provided by frappe / crm that our Links may point to.
EXTERNAL_DOCTYPES = {"User", "Contact", "Address", "CRM Organization", "CRM Deal", "File"}

VALID_FIELDTYPES = {
    "Attach", "Attach Image", "Check", "Column Break", "Currency", "Data", "Date",
    "Datetime", "Dynamic Link", "Float", "HTML", "Int", "Link", "Long Text",
    "Percent", "Read Only", "Section Break", "Select", "Small Text", "Tab Break",
    "Table", "Text", "Text Editor", "Time", "Button",
}


def scrub(name):
    return name.replace(" ", "_").lower()


def load(path):
    with open(path) as f:
        return json.load(f)


def child_tables():
    return {load(p)["name"]: load(p).get("istable", 0) for p in DOCTYPE_FILES}


def our_doctypes():
    return {load(p)["name"] for p in DOCTYPE_FILES}


def test_some_doctypes_exist():
    names = our_doctypes()
    assert {"Cabinet Client", "Cabinet Project", "Production Order",
            "Order Panel", "Order Material Line", "Stock Item", "Stock Location",
            "Stock Movement", "Stock Movement Item", "Stock Ledger Entry",
            "Cabinet Settings", "Cabinet Invoice", "Cabinet Invoice Item",
            "Payment Entry Lite"} <= names


def test_modules_have_packages():
    for m in MODULES:
        pkg = os.path.join(APP, scrub(m))
        assert os.path.isfile(os.path.join(pkg, "__init__.py")), m
        assert os.path.isfile(os.path.join(pkg, "doctype", "__init__.py")), m


@pytest.mark.parametrize("path", DOCTYPE_FILES, ids=lambda p: os.path.basename(p))
def test_doctype_json(path):
    d = load(path)
    folder = os.path.basename(os.path.dirname(path))

    assert d["doctype"] == "DocType"
    assert scrub(d["name"]) == folder == os.path.basename(path)[:-5]
    assert d["module"] in MODULES
    # module folder matches
    assert os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(path)))) == scrub(d["module"])

    # package files present
    assert os.path.isfile(os.path.join(os.path.dirname(path), "__init__.py"))
    assert os.path.isfile(os.path.join(os.path.dirname(path), f"{folder}.py"))

    fields = d["fields"]
    names = [f["fieldname"] for f in fields]
    assert len(names) == len(set(names)), "duplicate fieldnames"
    assert d["field_order"] == names
    known = our_doctypes() | EXTERNAL_DOCTYPES

    for f in fields:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", f["fieldname"]), f["fieldname"]
        assert f["fieldtype"] in VALID_FIELDTYPES, f
        if f["fieldtype"] in ("Link", "Table"):
            assert f.get("options") in known, f
        if f["fieldtype"] == "Table":
            assert child_tables().get(f["options"]) == 1, f"{f['options']} must be istable"
        if f["fieldtype"] == "Select" and f.get("default"):
            assert f["default"] in f["options"].split("\n"), f
        if f.get("fetch_from"):
            link, _, _ = f["fetch_from"].partition(".")
            assert link in names, f

    if d.get("title_field"):
        assert d["title_field"] in names
    for s in (d.get("search_fields") or "").split(","):
        if s.strip():
            assert s.strip() in names, s
    if not d.get("istable"):
        assert d["permissions"], "doctype needs at least one permission row"
    if d.get("is_submittable"):
        amended = [f for f in fields if f["fieldname"] == "amended_from"]
        assert amended and amended[0]["options"] == d["name"], "submittable needs amended_from"
        assert any(p.get("submit") and p.get("cancel") for p in d["permissions"])


def test_naming():
    by_name = {load(p)["name"]: load(p) for p in DOCTYPE_FILES}
    assert by_name["Cabinet Client"]["autoname"] == "C.####"
    assert by_name["Cabinet Project"]["autoname"] == "P.####"
    assert by_name["Production Order"]["autoname"] == "format:{project}-ORD-{##}"
    assert by_name["Cabinet Invoice"]["autoname"] == "INV-.YY.-.####"


def test_invoice_fields():
    inv = {f["fieldname"]: f for f in load(
        os.path.join(APP, "billing", "doctype", "cabinet_invoice", "cabinet_invoice.json"))["fields"]}
    for f in ("net_total", "cgst", "sgst", "igst", "grand_total", "rounded_total", "paid_amount",
              "outstanding_amount", "status", "place_of_supply", "due_date"):
        assert f in inv, f
    assert inv["status"]["options"].split("\n") == [
        "Draft", "Issued", "Unpaid", "Partly Paid", "Paid", "Overdue", "Cancelled"]
    for f in ("status", "paid_amount", "credited_amount", "outstanding_amount"):
        assert inv[f].get("allow_on_submit") == 1, f
    item = {f["fieldname"]: f for f in load(
        os.path.join(APP, "billing", "doctype", "cabinet_invoice_item", "cabinet_invoice_item.json"))["fields"]}
    assert item["gst_rate"]["options"].split("\n") == ["0", "5", "12", "18", "28"]


def test_scheduler_hook():
    hooks = open(os.path.join(APP, "hooks.py")).read()
    assert "cabinet_erp.billing.tasks.mark_overdue" in hooks


def test_order_panel_fields_match_parser():
    from cabinet_erp.production.f4p_import import PANEL_FIELDS
    panel = load(os.path.join(APP, "production", "doctype", "order_panel", "order_panel.json"))
    names = {f["fieldname"] for f in panel["fields"]}
    assert set(PANEL_FIELDS) <= names


def test_material_line_fields_match_parser():
    from cabinet_erp.production.f4p_import import parse_f4p
    line = load(os.path.join(APP, "production", "doctype", "order_material_line", "order_material_line.json"))
    names = {f["fieldname"] for f in line["fields"]}
    parsed = parse_f4p(os.path.join(ROOT, "tests", "fixtures", "f4p.sqlite"))
    assert set(parsed["material_lines"][0]) <= names


def test_production_order_fields_match_parser():
    from cabinet_erp.production.f4p_import import order_values, parse_f4p
    po = load(os.path.join(APP, "production", "doctype", "production_order", "production_order.json"))
    names = {f["fieldname"] for f in po["fields"]}
    parsed = parse_f4p(os.path.join(ROOT, "tests", "fixtures", "f4p.sqlite"))
    assert set(order_values(parsed)) <= names


def test_project_milestones():
    proj = {f["fieldname"]: f for f in load(
        os.path.join(APP, "clients", "doctype", "cabinet_project", "cabinet_project.json"))["fields"]}
    assert proj["milestone"]["options"].split("\n") == [
        "Enquiry", "Token Booked", "Advance Paid", "Design", "Confirmed",
        "Production", "Dispatched", "Installed", "Handover", "Closed",
    ]
    assert proj["milestone"]["default"] == "Enquiry"
    assert proj["client"]["reqd"] == 1


REPORT_FILES = sorted(glob.glob(os.path.join(APP, "*", "report", "*", "*.json")))


def test_reports_exist():
    names = {load(p)["name"] for p in REPORT_FILES}
    assert {"Stock Balance", "Stock Ledger", "Order Material Status", "Invoice Register",
            "Receivables Ageing", "Project Billing Summary"} <= names


@pytest.mark.parametrize("path", REPORT_FILES, ids=lambda p: os.path.basename(p))
def test_report_json(path):
    d = load(path)
    folder = os.path.dirname(path)
    assert d["doctype"] == "Report" and d["report_type"] == "Script Report"
    assert scrub(d["name"]) == os.path.basename(folder)
    assert d["module"] in MODULES and d["is_standard"] == "Yes"
    assert d["ref_doctype"] in our_doctypes()
    py = os.path.join(folder, os.path.basename(folder) + ".py")
    assert "def execute(" in open(py).read()
    assert os.path.isfile(os.path.join(folder, os.path.basename(folder) + ".js"))


def test_stock_ledger_entry_is_append_only():
    sle = load(os.path.join(APP, "inventory", "doctype", "stock_ledger_entry", "stock_ledger_entry.json"))
    assert sle["in_create"] == 1
    for p in sle["permissions"]:
        assert not p.get("write") and not p.get("create") and not p.get("delete")
