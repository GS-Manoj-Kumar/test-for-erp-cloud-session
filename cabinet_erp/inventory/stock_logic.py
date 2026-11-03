"""Stock rules as plain Python (NO Frappe imports) so they can be unit-tested with pytest.

A stock movement turns into "legs": ledger rows of
    {stock_item, location, state, qty_change, rate}
Balances are always sum(qty_change) per (location, state, stock_item).
"""

from collections import OrderedDict, defaultdict

RECEIVED = "Received"
IN_PROCESS = "In Process"
SENT = "Sent"
STATES = (RECEIVED, IN_PROCESS, SENT)

RECEIPT = "Receipt"
ISSUE = "Issue to Production"
RETURN = "Return from Production"
DISPATCH = "Dispatch"
TRANSFER = "Transfer"
MOVEMENT_TYPES = (RECEIPT, ISSUE, RETURN, DISPATCH, TRANSFER)

SCOPES = ("General", "Client", "Project", "Order")
# which link a scope needs, and the parents that get filled from it
SCOPE_LINK = {"General": None, "Client": "client", "Project": "project", "Order": "production_order"}

QTY_PRECISION = 6


class StockError(ValueError):
	pass


def _r(x):
	return round(float(x or 0), QTY_PRECISION)


# --- locations --------------------------------------------------------------

def location_errors(scope, client=None, project=None, production_order=None):
	if scope not in SCOPES:
		return [f"Unknown scope {scope!r}."]
	link = SCOPE_LINK[scope]
	values = {"client": client, "project": project, "production_order": production_order}
	if link and not values[link]:
		return [f"Scope {scope} needs {link.replace('_', ' ').title()}."]
	return []


def location_title(scope, client=None, project=None, production_order=None, names=None):
	"""Readable title. `names` may map ids to display names, e.g. {'C0001': 'Sharma'}."""
	names = names or {}

	def label(x):
		return f"{x} - {names[x]}" if names.get(x) else x

	if scope == "General":
		return "General Store"
	if scope == "Client":
		return f"Client: {label(client)}"
	if scope == "Project":
		return f"Project: {label(project)}"
	return f"Order: {label(production_order)}"


# --- movement -> ledger legs ------------------------------------------------

def movement_errors(movement_type, location, target_location=None, from_state=None,
                    items=None, location_project=None, target_project=None,
                    is_urgent=False, reason=None):
	"""Header/item checks that do not need balances. Returns a list of messages."""
	errors = []
	if movement_type not in MOVEMENT_TYPES:
		return [f"Unknown movement type {movement_type!r}."]
	if not location:
		errors.append("Location is required.")
	if movement_type == TRANSFER:
		if not target_location:
			errors.append("Target Location is required for a Transfer.")
		elif target_location == location:
			errors.append("Transfer needs two different locations.")
		elif needs_urgent_approval(location_project, target_project):
			if not is_urgent:
				errors.append("Project-to-project transfer must be marked Urgent.")
			if not (reason or "").strip():
				errors.append("Project-to-project transfer needs a Reason.")
	if movement_type == DISPATCH and from_state not in (RECEIVED, IN_PROCESS):
		errors.append("Dispatch must come from Received or In Process.")
	items = items or []
	if not items:
		errors.append("Add at least one item.")
	for i, it in enumerate(items, 1):
		if not it.get("stock_item"):
			errors.append(f"Row {i}: Stock Item is required.")
		if _r(it.get("qty")) <= 0:
			errors.append(f"Row {i}: Qty must be greater than 0.")
	return errors


def needs_urgent_approval(location_project, target_project):
	"""Moving stock that belongs to one project into another project."""
	return bool(location_project and target_project and location_project != target_project)


def movement_legs(movement_type, location, items, target_location=None, from_state=None):
	"""Ledger rows a submitted movement writes."""
	legs = []

	def leg(it, loc, state, sign):
		legs.append({
			"stock_item": it["stock_item"], "location": loc, "state": state,
			"qty_change": sign * _r(it["qty"]), "rate": _r(it.get("rate")),
		})

	for it in items:
		if movement_type == RECEIPT:
			leg(it, location, RECEIVED, +1)
		elif movement_type == ISSUE:
			leg(it, location, RECEIVED, -1)
			leg(it, location, IN_PROCESS, +1)
		elif movement_type == RETURN:
			leg(it, location, IN_PROCESS, -1)
			leg(it, location, RECEIVED, +1)
		elif movement_type == DISPATCH:
			leg(it, location, from_state, -1)
			leg(it, location, SENT, +1)
		elif movement_type == TRANSFER:
			leg(it, location, RECEIVED, -1)
			leg(it, target_location, RECEIVED, +1)
		else:
			raise StockError(f"Unknown movement type {movement_type!r}.")
	return legs


def reverse_legs(legs):
	"""Rows written on cancel: same rows, opposite sign. Ledger rows are never edited."""
	return [dict(l, qty_change=-l["qty_change"]) for l in legs]


def net_changes(legs):
	net = defaultdict(float)
	for l in legs:
		net[(l["location"], l["state"], l["stock_item"])] += l["qty_change"]
	return {k: _r(v) for k, v in net.items()}


def shortage_errors(legs, balance_of):
	"""Check no (location, state, item) goes below zero.

	`balance_of(location, state, stock_item)` returns the current balance.
	Legs are netted first, so one movement with the same item twice is checked as a whole.
	"""
	errors = []
	for (loc, state, item), change in net_changes(legs).items():
		if change >= 0:
			continue
		have = _r(balance_of(loc, state, item))
		if _r(have + change) < 0:
			errors.append(
				f"Not enough {item} in {loc} ({state}): have {have:g}, need {-change:g}."
			)
	return errors


def apply_legs(balances, legs):
	"""Return a new balances dict {(loc, state, item): qty} with legs applied."""
	out = dict(balances)
	for k, v in net_changes(legs).items():
		out[k] = _r(out.get(k, 0) + v)
	return out


# --- report helpers ---------------------------------------------------------

def pivot_balances(rows):
	"""rows: iterable of {location, stock_item, state, qty}. Returns one row per
	(location, stock_item) with received / in_process / sent / total columns,
	ordered by location then item, zero rows dropped."""
	key = {RECEIVED: "received", IN_PROCESS: "in_process", SENT: "sent"}
	acc = OrderedDict()
	for r in sorted(rows, key=lambda r: (r["location"], r["stock_item"])):
		k = (r["location"], r["stock_item"])
		row = acc.setdefault(k, {"location": k[0], "stock_item": k[1],
		                         "received": 0.0, "in_process": 0.0, "sent": 0.0})
		row[key[r["state"]]] = _r(row[key[r["state"]]] + r["qty"])
	out = []
	for row in acc.values():
		row["total"] = _r(row["received"] + row["in_process"] + row["sent"])
		if row["received"] or row["in_process"] or row["sent"]:
			out.append(row)
	return out


def material_status(lines, stock):
	"""Required vs stock for one order.

	lines: [{stock_item, description, kind, order_qty}] (Order Material Lines)
	stock: {stock_item: {"received": x, "in_process": y, "sent": z}} for that order
	Returns rows with required, received, in_process, sent, shortfall. Lines without a
	mapped stock_item are listed with zero stock. Stock items held for the order but
	not on any line are added at the end with required 0.
	"""
	required = OrderedDict()
	unmapped = []
	for l in lines:
		item = l.get("stock_item")
		if not item:
			unmapped.append(l)
			continue
		row = required.setdefault(item, {"stock_item": item, "description": l.get("description") or "",
		                                 "kind": l.get("kind") or "", "required": 0.0})
		row["required"] = _r(row["required"] + _r(l.get("order_qty") or l.get("qty")))

	for item in stock:
		required.setdefault(item, {"stock_item": item, "description": "", "kind": "", "required": 0.0})

	out = []
	for item, row in required.items():
		s = stock.get(item, {})
		row.update(received=_r(s.get("received")), in_process=_r(s.get("in_process")), sent=_r(s.get("sent")))
		row["shortfall"] = max(_r(row["required"] - row["received"] - row["in_process"] - row["sent"]), 0.0)
		out.append(row)
	for l in unmapped:
		req = _r(l.get("order_qty") or l.get("qty"))
		out.append({"stock_item": "", "description": l.get("description") or "", "kind": l.get("kind") or "",
		            "required": req, "received": 0.0, "in_process": 0.0, "sent": 0.0, "shortfall": req})
	return out


def running_balances(opening, rows):
	"""Add a `balance` to each ledger row: running qty per (location, state, stock_item),
	starting from `opening` {(location, state, item): qty} (balance before the date range)."""
	bal = dict(opening)
	out = []
	for r in rows:
		k = (r["location"], r["state"], r["stock_item"])
		bal[k] = _r(bal.get(k, 0) + r["qty_change"])
		out.append(dict(r, balance=bal[k]))
	return out


# --- report filters (shared by the Script Reports) --------------------------

FILTER_COLUMNS = {
	"client": "client",
	"project": "project",
	"production_order": "production_order",
	"stock_item": "stock_item",
	"state": "state",
	"location": "location",
}


def ledger_conditions(filters, from_date=True, to_date=True):
	"""SQL WHERE fragment + params for Stock Ledger Entry reports.

	Only fixed column names are used; values always go through params."""
	filters = filters or {}
	clauses, params = ["1=1"], {}
	for key, col in FILTER_COLUMNS.items():
		if filters.get(key):
			clauses.append(f"`{col}` = %({key})s")
			params[key] = filters[key]
	if from_date and filters.get("from_date"):
		clauses.append("posting_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if to_date and filters.get("to_date"):
		clauses.append("posting_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	return " and ".join(clauses), params
