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


def our_doctypes():
    return {load(p)["name"] for p in DOCTYPE_FILES}


def test_some_doctypes_exist():
    names = our_doctypes()
    assert {"Cabinet Client", "Cabinet Project"} <= names


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
    assert d["permissions"], "doctype needs at least one permission row"


def test_naming():
    by_name = {load(p)["name"]: load(p) for p in DOCTYPE_FILES}
    assert by_name["Cabinet Client"]["autoname"] == "C.####"
    assert by_name["Cabinet Project"]["autoname"] == "P.####"


def test_project_milestones():
    proj = {f["fieldname"]: f for f in load(
        os.path.join(APP, "clients", "doctype", "cabinet_project", "cabinet_project.json"))["fields"]}
    assert proj["milestone"]["options"].split("\n") == [
        "Enquiry", "Token Booked", "Advance Paid", "Design", "Confirmed",
        "Production", "Dispatched", "Installed", "Handover", "Closed",
    ]
    assert proj["milestone"]["default"] == "Enquiry"
    assert proj["client"]["reqd"] == 1
