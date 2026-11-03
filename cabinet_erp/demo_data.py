"""Dummy business data used by the static demo site (scripts/build_demo_site.py) and by
the live demo loader (cabinet_erp/demo.py). Pure Python, no Frappe imports.

All names, GSTINs, phone numbers and amounts are made up.
"""

from cabinet_erp.utils.gst import gstin_checksum

DEMO_TODAY = "2026-11-03"


def demo_gstin(state_code, pan):
	"""A format-valid (but fictional) GSTIN: state code + 10-char PAN + 1 + Z + check digit."""
	first14 = f"{state_code}{pan}1Z"
	return first14 + gstin_checksum(first14)


COMPANY = {
	"company_name": "Demo Cabinets Pvt Ltd",
	"company_gstin": demo_gstin("29", "AABCD1234E"),
	"company_state": "Karnataka",
	"default_gst_rate": "18",
	"default_due_days": 15,
}

CLIENTS = [
	{"key": "C0001", "client_name": "Anita Sharma", "client_type": "B2C", "phone": "+91 90000 00001",
	 "email": "anita.sharma@example.com", "state": "Karnataka",
	 "billing_address": "Flat 1203, Palm Grove Apartments, Whitefield, Bengaluru 560066"},
	{"key": "C0002", "client_name": "Lotus Interiors Pvt Ltd", "client_type": "B2B", "phone": "+91 90000 00002",
	 "email": "accounts@lotus-interiors.example.com", "state": "Karnataka",
	 "gstin": demo_gstin("29", "AAECL5678K"),
	 "billing_address": "4th Floor, 80 Feet Road, Koramangala, Bengaluru 560034"},
	{"key": "C0003", "client_name": "Greenfield Builders LLP", "client_type": "B2B", "phone": "+91 90000 00003",
	 "email": "projects@greenfield.example.com", "state": "Maharashtra",
	 "gstin": demo_gstin("27", "AAKFG4321M"),
	 "billing_address": "Survey 12, Baner Road, Pune 411045"},
]

PROJECTS = [
	{"key": "P0001", "client": "C0001", "project_name": "Whitefield 3BHK", "property_type": "Apartment",
	 "milestone": "Production", "token_booking": "2026-08-10", "advance_paid": "2026-08-25",
	 "confirmation": "2026-09-05", "target_handover": "2026-12-15", "estimated_handover": "2026-12-20",
	 "nas_path": r"\\NAS\Projects\C0001_Anita-Sharma\P0001_Whitefield-3BHK"},
	{"key": "P0002", "client": "C0002", "project_name": "Koramangala office fit-out", "property_type": "Office",
	 "milestone": "Design", "token_booking": "2026-10-01", "target_handover": "2027-01-31",
	 "nas_path": r"\\NAS\Projects\C0002_Lotus-Interiors\P0002_Koramangala-office"},
	{"key": "P0003", "client": "C0003", "project_name": "Baner show flat", "property_type": "Apartment",
	 "milestone": "Dispatched", "token_booking": "2026-07-15", "advance_paid": "2026-07-20",
	 "confirmation": "2026-08-01", "target_handover": "2026-10-31", "estimated_handover": "2026-11-10",
	 "nas_path": r"\\NAS\Projects\C0003_Greenfield-Builders\P0003_Baner-show-flat"},
	{"key": "P0004", "client": "C0001", "project_name": "Villa wardrobes", "property_type": "Villa",
	 "milestone": "Enquiry", "token_booking": "2026-10-28"},
]

STOCK_ITEMS = [
	{"item_code": "CORE-18-8X4", "item_name": "18mm MR ply core 8x4", "kind": "Core Sheet", "uom": "Sheet",
	 "thickness": 18, "size_label": "8X4", "default_rate": 2450},
	{"item_code": "CORE-15-8X4", "item_name": "15mm MR ply core 8x4", "kind": "Core Sheet", "uom": "Sheet",
	 "thickness": 15, "size_label": "8X4", "default_rate": 2200},
	{"item_code": "CORE-8-8X4", "item_name": "8mm MR ply core 8x4", "kind": "Core Sheet", "uom": "Sheet",
	 "thickness": 8, "size_label": "8X4", "default_rate": 1400},
	{"item_code": "LAM-WALNUT-1MM", "item_name": "Walnut bronze laminate 1mm", "kind": "Laminate", "uom": "Sheet",
	 "thickness": 1, "size_label": "8X4", "color": "Walnut bronze", "default_rate": 1800},
	{"item_code": "EB-045", "item_name": "Edge band 0.45mm", "kind": "Edge Band", "uom": "m", "thickness": 0.45, "default_rate": 9},
	{"item_code": "EB-08", "item_name": "Edge band 0.8mm", "kind": "Edge Band", "uom": "m", "thickness": 0.8, "default_rate": 12},
	{"item_code": "EB-10", "item_name": "Edge band 1.0mm", "kind": "Edge Band", "uom": "m", "thickness": 1.0, "default_rate": 15},
	{"item_code": "EB-20", "item_name": "Edge band 2.0mm", "kind": "Edge Band", "uom": "m", "thickness": 2.0, "default_rate": 22},
	{"item_code": "GLUE-PVA", "item_name": "PVA wood glue", "kind": "Glue", "uom": "kg", "default_rate": 320},
	{"item_code": "HINGE-SC", "item_name": "Soft-close hinge", "kind": "Hardware", "uom": "Nos", "default_rate": 145},
]
ITEM_RATE = {i["item_code"]: i["default_rate"] for i in STOCK_ITEMS}


def stock_item_for_line(kind, description):
	"""Map an F4P material line to a demo stock item (core by thickness, edge band by thickness)."""
	d = (description or "").strip()
	if kind == "core":
		thick = d.replace("mm", "").strip()
		return {"18.0": "CORE-18-8X4", "15.0": "CORE-15-8X4", "8.0": "CORE-8-8X4"}.get(thick)
	if kind == "edge_band":
		for t, code in (("0.45mm", "EB-045"), ("0.8mm", "EB-08"), ("1.0mm", "EB-10"), ("2.0mm", "EB-20")):
			if f"_{t}" in d:
				return code
	if kind == "laminate":
		return "LAM-WALNUT-1MM"
	if kind == "glue":
		return "GLUE-PVA"
	return None


ORDERS = [
	# Panels + material lines come from tests/fixtures/f4p.sqlite (the sample seal).
	{"key": "P0001-ORD-01", "project": "P0001", "order_title": "Kitchen and utility", "status": "Cutting",
	 "import_fixture": True},
	{"key": "P0001-ORD-02", "project": "P0001", "order_title": "Wardrobes", "status": "Draft"},
	{"key": "P0003-ORD-01", "project": "P0003", "order_title": "Show-flat kitchen", "status": "Dispatched",
	 "material_lines": [
		{"kind": "core", "description": "18.0mm", "size": "8X4", "qty": 10, "order_qty": 11, "wastage_pct": 5},
		{"kind": "laminate", "description": "Walnut bronze 1mm", "size": "8X4", "qty": 6, "order_qty": 7, "wastage_pct": 5},
		{"kind": "edge_band", "description": "C4_1.0mm 26.5m", "size": "", "qty": 26.5, "order_qty": 28, "wastage_pct": 5},
	 ]},
]

# Locations other than the General Store (which every site has).
LOCATIONS = [
	{"key": "LOC-0002", "scope": "Project", "project": "P0001"},
	{"key": "LOC-0003", "scope": "Order", "production_order": "P0001-ORD-01"},
	{"key": "LOC-0004", "scope": "Order", "production_order": "P0003-ORD-01"},
]
GENERAL = "LOC-0001"


# Submitted in this order (dates ascending per location).
MOVEMENTS = [
	{"key": "SM-26-00001", "movement_type": "Receipt", "posting_date": "2026-08-20", "location": "LOC-0004",
	 "remarks": "Material for Baner show flat", "items": [
		{"stock_item": "CORE-18-8X4", "qty": 12}, {"stock_item": "LAM-WALNUT-1MM", "qty": 7},
		{"stock_item": "EB-10", "qty": 30}, {"stock_item": "HINGE-SC", "qty": 24}]},
	{"key": "SM-26-00002", "movement_type": "Issue to Production", "posting_date": "2026-08-25", "location": "LOC-0004",
	 "items": [{"stock_item": "CORE-18-8X4", "qty": 11}, {"stock_item": "LAM-WALNUT-1MM", "qty": 7},
	           {"stock_item": "EB-10", "qty": 28}, {"stock_item": "HINGE-SC", "qty": 24}]},
	{"key": "SM-26-00003", "movement_type": "Receipt", "posting_date": "2026-09-01", "location": GENERAL,
	 "remarks": "Monthly purchase", "items": [
		{"stock_item": "CORE-18-8X4", "qty": 20}, {"stock_item": "CORE-15-8X4", "qty": 4},
		{"stock_item": "CORE-8-8X4", "qty": 4}, {"stock_item": "LAM-WALNUT-1MM", "qty": 10},
		{"stock_item": "EB-045", "qty": 10}, {"stock_item": "EB-08", "qty": 10},
		{"stock_item": "EB-10", "qty": 50}, {"stock_item": "EB-20", "qty": 20},
		{"stock_item": "GLUE-PVA", "qty": 5}, {"stock_item": "HINGE-SC", "qty": 40}]},
	{"key": "SM-26-00004", "movement_type": "Transfer", "posting_date": "2026-09-12", "location": GENERAL,
	 "target_location": "LOC-0003", "remarks": "Book material for kitchen order", "items": [
		{"stock_item": "CORE-18-8X4", "qty": 8}, {"stock_item": "CORE-15-8X4", "qty": 2},
		{"stock_item": "CORE-8-8X4", "qty": 2}, {"stock_item": "EB-045", "qty": 1},
		{"stock_item": "EB-08", "qty": 2}, {"stock_item": "EB-10", "qty": 10}, {"stock_item": "EB-20", "qty": 5}]},
	{"key": "SM-26-00005", "movement_type": "Issue to Production", "posting_date": "2026-09-15", "location": "LOC-0003",
	 "items": [{"stock_item": "CORE-18-8X4", "qty": 6}, {"stock_item": "CORE-15-8X4", "qty": 2},
	           {"stock_item": "CORE-8-8X4", "qty": 2}, {"stock_item": "EB-10", "qty": 8}]},
	{"key": "SM-26-00006", "movement_type": "Dispatch", "posting_date": "2026-10-05", "location": "LOC-0004",
	 "from_state": "In Process", "remarks": "Delivered to Baner site", "items": [
		{"stock_item": "CORE-18-8X4", "qty": 11}, {"stock_item": "LAM-WALNUT-1MM", "qty": 7},
		{"stock_item": "EB-10", "qty": 28}, {"stock_item": "HINGE-SC", "qty": 24}]},
	{"key": "SM-26-00007", "movement_type": "Transfer", "posting_date": "2026-10-20", "location": "LOC-0004",
	 "target_location": "LOC-0002", "is_urgent": 1,
	 "reason": "Whitefield site is one 18mm sheet short; Baner leftover sheet sent over.",
	 "items": [{"stock_item": "CORE-18-8X4", "qty": 1}]},
	{"key": "SM-26-00008", "movement_type": "Return from Production", "posting_date": "2026-10-25",
	 "location": "LOC-0003", "remarks": "Unused edge band back from the line",
	 "items": [{"stock_item": "EB-10", "qty": 1}]},
]
for _m in MOVEMENTS:
	for _it in _m["items"]:
		_it.setdefault("rate", ITEM_RATE[_it["stock_item"]])

INVOICES = [
	{"key": "INV-26-0001", "invoice_type": "Tax Invoice", "client": "C0001", "project": "P0001",
	 "production_order": "P0001-ORD-01", "posting_date": "2026-09-06", "due_date": "2026-09-21",
	 "items": [
		{"description": "Modular kitchen - carcass and shutters", "hsn_sac": "9403", "qty": 1, "uom": "Nos", "rate": 285000, "gst_rate": "18"},
		{"description": "Installation", "hsn_sac": "9954", "qty": 1, "uom": "Nos", "rate": 15000, "gst_rate": "18"}]},
	{"key": "INV-26-0002", "invoice_type": "Tax Invoice", "client": "C0003", "project": "P0003",
	 "production_order": "P0003-ORD-01", "posting_date": "2026-08-28", "due_date": "2026-09-12",
	 "items": [{"description": "Show-flat kitchen supply", "hsn_sac": "9403", "qty": 1, "uom": "Nos", "rate": 180000, "gst_rate": "18"}]},
	{"key": "INV-26-0003", "invoice_type": "Credit Note", "client": "C0003", "project": "P0003",
	 "return_against": "INV-26-0002", "posting_date": "2026-10-10",
	 "items": [{"description": "Discount for delayed dispatch", "hsn_sac": "9403", "qty": 1, "uom": "Nos", "rate": 10000, "gst_rate": "18"}]},
	{"key": "INV-26-0004", "invoice_type": "Proforma", "client": "C0002", "project": "P0002", "posting_date": "2026-10-12",
	 "items": [{"description": "Office workstations (40 seats)", "hsn_sac": "9403", "qty": 40, "uom": "Nos", "rate": 16000, "gst_rate": "18"}]},
	{"key": "INV-26-0005", "invoice_type": "Quotation", "client": "C0001", "project": "P0004", "posting_date": "2026-10-28",
	 "items": [{"description": "Villa wardrobes with loft", "hsn_sac": "9403", "qty": 4, "uom": "Nos", "rate": 62000, "gst_rate": "18"}]},
	{"key": "INV-26-0006", "invoice_type": "Tax Invoice", "client": "C0002", "project": "P0002", "posting_date": "2026-10-30",
	 "due_date": "2026-11-14",
	 "items": [{"description": "Design and working drawings", "hsn_sac": "998391", "qty": 1, "uom": "Nos", "rate": 50000, "gst_rate": "18"}]},
]

PAYMENTS = [
	{"key": "PAY-26-0001", "client": "C0001", "invoice": "INV-26-0001", "posting_date": "2026-09-08",
	 "amount": 150000, "mode": "UPI", "reference_no": "UPI-DEMO-1001"},
	{"key": "PAY-26-0002", "client": "C0003", "invoice": "INV-26-0002", "posting_date": "2026-09-30",
	 "amount": 120000, "mode": "Cheque", "reference_no": "CHQ-004512"},
	{"key": "PAY-26-0003", "client": "C0001", "invoice": "INV-26-0001", "posting_date": "2026-10-15",
	 "amount": 100000, "mode": "NEFT/RTGS", "reference_no": "UTR-DEMO-2002"},
]


def priced_lines(lines):
	"""Give material lines demo prices + stock items (the sample seal has zero prices)."""
	out = []
	for l in lines:
		item = stock_item_for_line(l["kind"], l["description"])
		price = ITEM_RATE.get(item, 0)
		out.append(dict(l, stock_item=item, unit_price=price,
		                line_total=round(float(l.get("order_qty") or 0) * price, 2)))
	return out


def line_costs(lines):
	costs = {"cost_core": 0.0, "cost_laminate": 0.0, "cost_glue": 0.0, "cost_edge_band": 0.0}
	for l in lines:
		costs[f"cost_{l['kind']}"] = round(costs.get(f"cost_{l['kind']}", 0) + l["line_total"], 2)
	costs["cost_grand"] = round(sum(costs.values()), 2)
	return costs
