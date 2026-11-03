"""Read a sealed F4P database (f4p.sqlite) into plain Python data.

Pure Python: NO Frappe imports here, so it can be tested with plain pytest.
The Frappe side (writing Production Order / Order Panel rows) lives in
production/doctype/production_order/production_order.py and calls into this module.
"""

import os
import sqlite3
from urllib.parse import quote

SUPPORTED_SCHEMA_VERSION = 7
COST_KINDS = ("core", "laminate", "glue", "edge_band", "grand")
MATERIAL_KINDS = ("core", "laminate", "glue", "edge_band")
# meta values that old seals use to mean "not set"
EMPTY_CODES = {"", "NO_PROJECT", "NONE", "NULL"}

PANEL_FIELDS = (
	"panel_id", "panel_index", "quantity", "code_name_1", "code_name_2", "code_name_3",
	"shape_type", "thickness", "material_name", "finished_length", "finished_width",
	"area", "grain", "edge_band_summary", "sheet_index", "board_index", "pack_group",
	"exclusion_status", "warnings",
)


class F4PError(ValueError):
	"""The file cannot be imported (not a sealed DB, wrong schema, ...)."""


def _connect_ro(path):
	if not os.path.isfile(path):
		raise F4PError(f"F4P file not found: {path}")
	uri = "file:" + quote(os.path.abspath(path)) + "?mode=ro"
	try:
		conn = sqlite3.connect(uri, uri=True)
		conn.row_factory = sqlite3.Row
		conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
	except sqlite3.DatabaseError as e:
		raise F4PError(f"Not a valid SQLite file: {e}") from e
	return conn


def _objects(conn):
	return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}


def _int(v, default=0):
	try:
		return int(float(v))
	except (TypeError, ValueError):
		return default


def _float(v, default=0.0):
	try:
		return float(v)
	except (TypeError, ValueError):
		return default


def _text(v):
	return "" if v is None else str(v).strip()


def _read_meta(conn):
	return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}


def _read_panels(conn, objects):
	placement = {}
	if "v_mastercutlist" in objects:
		# one row per panel expected; if a panel appears more than once keep the first sheet
		for r in conn.execute(
			"SELECT panel_id, sheet_index, board_index FROM v_mastercutlist ORDER BY sheet_index, board_index"
		):
			placement.setdefault(r["panel_id"], (r["sheet_index"], r["board_index"]))

	groups = {}
	if "pack_item" in objects:
		for r in conn.execute("SELECT panel_id, group_code FROM pack_item"):
			groups.setdefault(r["panel_id"], r["group_code"])

	panels = []
	for r in conn.execute("SELECT * FROM panel ORDER BY panel_index, panel_id"):
		sheet_index, board_index = placement.get(r["panel_id"], (None, None))
		panels.append(
			{
				"panel_id": _text(r["panel_id"]),
				"panel_index": _int(r["panel_index"]),
				"quantity": _int(r["quantity"], 1),
				"code_name_1": _text(r["code_name_1"]),
				"code_name_2": _text(r["code_name_2"]),
				"code_name_3": _text(r["code_name_3"]),
				"shape_type": _text(r["shape_type"]),
				"thickness": _float(r["thickness"]),
				"material_name": _text(r["material_name"]),
				"finished_length": _float(r["finished_length"]),
				"finished_width": _float(r["finished_width"]),
				"area": _float(r["area"]),
				"grain": _text(r["grain"]),
				"edge_band_summary": _text(r["edge_band_summary"]),
				"sheet_index": sheet_index,
				"board_index": board_index,
				"pack_group": _text(groups.get(r["panel_id"])),
				"exclusion_status": _text(r["exclusion_status"]),
				"warnings": _text(r["warnings"]),
			}
		)
	return panels


def _read_material_lines(conn, objects):
	if "material_cost" not in objects:
		return []
	lines = []
	for r in conn.execute("SELECT * FROM material_cost ORDER BY cost_id"):
		lines.append(
			{
				"kind": _text(r["kind"]),
				"description": _text(r["description"]),  # source has leading spaces
				"size": _text(r["size"]),
				"qty": _float(r["qty"]),
				"order_qty": _float(r["order_qty"]),
				"wastage_pct": _float(r["wastage_pct"]),
				"unit_price": _float(r["unit_price"]),
				"line_total": _float(r["line_total"]),
			}
		)
	return lines


def _read_costs(conn, objects):
	costs = {k: 0.0 for k in COST_KINDS}
	if "cost_total" in objects:
		for r in conn.execute("SELECT kind, amount FROM cost_total"):
			kind = _text(r["kind"])
			if kind and not kind.startswith("_"):
				costs[kind] = _float(r["amount"])
	return costs


def parse_f4p(path):
	"""Parse a sealed f4p.sqlite. Returns a dict; raises F4PError if it can't be imported.

	Keys: seal_id, sealed_at, sealer_version, skp_name, schema_version, panel_count,
	variety_count, sheet_count, project_code, client_code, order_no, meta (raw),
	panels (list of dicts), material_lines (list of dicts), costs (kind -> amount).
	"""
	conn = _connect_ro(path)
	try:
		objects = _objects(conn)
		missing = {"meta", "panel"} - objects
		if missing:
			raise F4PError(f"Not a sealed F4P database (missing table: {', '.join(sorted(missing))}).")

		meta = _read_meta(conn)
		found = _text(meta.get("schema_version"))
		if found != str(SUPPORTED_SCHEMA_VERSION):
			raise F4PError(
				f"Unsupported F4P schema_version {found or '(missing)'}; "
				f"this importer needs schema_version {SUPPORTED_SCHEMA_VERSION}. Re-seal with a current sealer."
			)
		seal_id = _text(meta.get("seal_id"))
		if not seal_id:
			raise F4PError("F4P file has no seal_id; it was not sealed.")

		panels = _read_panels(conn, objects)
		sheet_count = conn.execute("SELECT COUNT(*) FROM sheet").fetchone()[0] if "sheet" in objects else 0

		return {
			"seal_id": seal_id,
			"sealed_at": _text(meta.get("sealed_at")).replace("T", " "),
			"sealer_version": _text(meta.get("sealer_version")),
			"skp_name": _text(meta.get("skp_name")),
			"schema_version": int(found),
			"panel_count": _int(meta.get("panel_count"), len(panels)),
			"variety_count": _int(meta.get("variety_count")),
			"sheet_count": sheet_count,
			"project_code": _text(meta.get("project_code")),
			"client_code": _text(meta.get("client_code")),
			"order_no": _text(meta.get("order_no")),
			"meta": meta,
			"panels": panels,
			"material_lines": _read_material_lines(conn, objects),
			"costs": _read_costs(conn, objects),
		}
	finally:
		conn.close()


def plan_import(existing_seal_id, parsed):
	"""Decide what an import does: 'new' (no data yet), 'skip' (same seal), 'replace'."""
	if not existing_seal_id:
		return "new"
	if existing_seal_id == parsed["seal_id"]:
		return "skip"
	return "replace"


def _is_set(code):
	return _text(code).upper() not in EMPTY_CODES


def meta_warnings(parsed, project=None, client=None, order=None):
	"""Warnings when the seal's own project/client/order codes disagree with the order
	being imported into. Never blocks: the order the user picked always wins."""
	warnings = []
	if project and _is_set(parsed.get("project_code")) and parsed["project_code"] != project:
		warnings.append(f"F4P project_code is {parsed['project_code']}, but this order belongs to project {project}.")
	if client and _is_set(parsed.get("client_code")) and parsed["client_code"] != client:
		warnings.append(f"F4P client_code is {parsed['client_code']}, but this order belongs to client {client}.")
	if order and _is_set(parsed.get("order_no")):
		order_no = parsed["order_no"]
		suffix = order.rsplit("-ORD-", 1)[-1] if "-ORD-" in order else order
		accepted = {order, suffix, f"ORD-{suffix}"}
		if order_no not in accepted and order_no.lstrip("0") != suffix.lstrip("0"):
			warnings.append(f"F4P order_no is {order_no}, but you are importing into order {order}.")
	return warnings


def order_values(parsed):
	"""Field values to set on the Production Order (header + costs)."""
	costs = parsed["costs"]
	return {
		"seal_id": parsed["seal_id"],
		"sealed_at": parsed["sealed_at"] or None,
		"sealer_version": parsed["sealer_version"],
		"skp_name": parsed["skp_name"],
		"panel_count": parsed["panel_count"],
		"variety_count": parsed["variety_count"],
		"sheet_count": parsed["sheet_count"],
		"cost_core": costs.get("core", 0.0),
		"cost_laminate": costs.get("laminate", 0.0),
		"cost_glue": costs.get("glue", 0.0),
		"cost_edge_band": costs.get("edge_band", 0.0),
		"cost_grand": costs.get("grand", 0.0),
	}
