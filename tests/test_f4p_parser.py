"""Tests for the pure-Python F4P parser. Runs with plain pytest, no bench."""

import os
import shutil
import sqlite3

import pytest

from cabinet_erp.production.f4p_import import (
    PANEL_FIELDS,
    F4PError,
    meta_warnings,
    order_values,
    parse_f4p,
    plan_import,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "f4p.sqlite")


@pytest.fixture(scope="module")
def parsed():
    return parse_f4p(FIXTURE)


def _copy_with_meta(tmp_path, **changes):
    dst = tmp_path / "f4p.sqlite"
    shutil.copy(FIXTURE, dst)
    conn = sqlite3.connect(dst)
    for k, v in changes.items():
        conn.execute("UPDATE meta SET value = ? WHERE key = ?", (v, k))
    conn.commit()
    conn.close()
    return str(dst)


# --- schema check -----------------------------------------------------------

def test_schema_version_ok(parsed):
    assert parsed["schema_version"] == 7


def test_wrong_schema_version_refused(tmp_path):
    path = _copy_with_meta(tmp_path, schema_version="6")
    with pytest.raises(F4PError, match="schema_version 6"):
        parse_f4p(path)


def test_missing_file(tmp_path):
    with pytest.raises(F4PError, match="not found"):
        parse_f4p(str(tmp_path / "nope.sqlite"))


def test_not_sqlite(tmp_path):
    p = tmp_path / "junk.sqlite"
    p.write_bytes(b"this is not a database at all" * 50)
    with pytest.raises(F4PError):
        parse_f4p(str(p))


def test_opened_read_only(tmp_path):
    path = _copy_with_meta(tmp_path)
    before = open(path, "rb").read()
    parse_f4p(path)
    assert open(path, "rb").read() == before


# --- panels -----------------------------------------------------------------

def test_panel_count(parsed):
    assert len(parsed["panels"]) == 88
    assert parsed["panel_count"] == 88


def test_panel_fields_and_placement(parsed):
    for p in parsed["panels"]:
        assert set(p) == set(PANEL_FIELDS)
    by_id = {p["panel_id"]: p for p in parsed["panels"]}
    p10 = by_id["__10"]
    assert p10["sheet_index"] == 0 and p10["board_index"] == 3   # from v_mastercutlist
    assert p10["pack_group"] == "1_tb_bb"                        # from pack_item.group_code
    assert p10["thickness"] == 18.0
    assert p10["material_name"] == "MERINO_10510_MAGAS_WALNUT_BRONZE"
    assert all(p["pack_group"] for p in parsed["panels"])


def test_header_counts(parsed):
    assert parsed["variety_count"] == 4
    assert parsed["sheet_count"] == 9
    assert parsed["skp_name"] == "test_case_31"
    assert parsed["sealer_version"] == "1.9.7"
    assert parsed["sealed_at"] == "2026-09-11 23:50:02"


# --- material lines & costs -------------------------------------------------

def test_material_lines(parsed):
    lines = parsed["material_lines"]
    assert len(lines) == 12
    assert {l["kind"] for l in lines} <= {"core", "laminate", "glue", "edge_band"}
    assert lines[0]["description"] == "15.0mm"           # leading spaces stripped
    assert all(l["description"] == l["description"].strip() for l in lines)
    assert lines[0]["order_qty"] == 2.0 and lines[0]["wastage_pct"] == 5.0


def test_cost_keys(parsed):
    assert set(parsed["costs"]) == {"core", "laminate", "glue", "edge_band", "grand"}
    assert not any(k.startswith("_") for k in parsed["costs"])


def test_order_values(parsed):
    v = order_values(parsed)
    assert v["seal_id"] == "20260911_235002"
    assert v["sheet_count"] == 9
    assert set(k for k in v if k.startswith("cost_")) == {
        "cost_core", "cost_laminate", "cost_glue", "cost_edge_band", "cost_grand"}


# --- idempotency ------------------------------------------------------------

def test_idempotency_key_is_seal_id(parsed):
    assert parsed["seal_id"] == "20260911_235002"
    assert plan_import(None, parsed) == "new"
    assert plan_import("", parsed) == "new"
    assert plan_import("20260911_235002", parsed) == "skip"
    assert plan_import("20250101_000000", parsed) == "replace"


def test_missing_seal_id_refused(tmp_path):
    with pytest.raises(F4PError, match="seal_id"):
        parse_f4p(_copy_with_meta(tmp_path, seal_id=""))


# --- meta codes never trusted, only warned ----------------------------------

def test_no_project_codes_give_no_warning(parsed):
    # fixture has project_code NO_PROJECT and empty client_code / order_no
    assert meta_warnings(parsed, project="P0001", client="C0001", order="P0001-ORD-01") == []


def test_disagreeing_codes_warn():
    p = {"project_code": "P0002", "client_code": "C0009", "order_no": "03"}
    w = meta_warnings(p, project="P0001", client="C0001", order="P0001-ORD-01")
    assert len(w) == 3


def test_matching_codes_no_warning():
    for order_no in ("01", "1", "ORD-01", "P0001-ORD-01"):
        p = {"project_code": "P0001", "client_code": "C0001", "order_no": order_no}
        assert meta_warnings(p, project="P0001", client="C0001", order="P0001-ORD-01") == [], order_no
