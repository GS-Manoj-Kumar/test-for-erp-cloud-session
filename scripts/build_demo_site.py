"""Build the static demo site's data (site/data.json) from cabinet_erp/demo_data.py.

Every number goes through the app's own pure-Python logic (F4P parser, stock rules,
GST / outstanding / status rules), so the demo shows what the real app computes.

    python scripts/build_demo_site.py          # writes site/data.json
    python -m http.server -d site 8080         # open http://localhost:8080
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cabinet_erp import demo_data as D  # noqa: E402
from cabinet_erp.billing.billing_logic import (  # noqa: E402
	CREDIT_NOTE, TAX_INVOICE, ageing_row, compute_invoice, credit_note_errors, invoice_status,
	outstanding, payment_errors, project_summary,
)
from cabinet_erp.inventory.stock_logic import (  # noqa: E402
	IN_PROCESS, RECEIVED, SENT, apply_legs, location_title, material_status, movement_errors,
	movement_legs, needs_urgent_approval, pivot_balances, running_balances, shortage_errors,
)
from cabinet_erp.production.f4p_import import order_values, parse_f4p  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "f4p.sqlite")


def by_key(rows):
	return {r["key"]: r for r in rows}


def strip_key(d):
	d = dict(d)
	d["name"] = d.pop("key")
	return d


def build():
	today = D.DEMO_TODAY
	clients = {c["key"]: strip_key(c) for c in D.CLIENTS}
	projects = {}
	for p in D.PROJECTS:
		doc = strip_key(p)
		c = clients[doc["client"]]
		doc.update(client_name=c["client_name"], project_type=c["client_type"])
		projects[doc["name"]] = doc

	# --- production ---------------------------------------------------------
	orders, panels = {}, []
	for o in D.ORDERS:
		doc = strip_key(o)
		doc.pop("import_fixture", None)
		p = projects[doc["project"]]
		doc.update(project_name=p["project_name"], client=p["client"], client_name=p["client_name"])
		lines = o.get("material_lines") or []
		if o.get("import_fixture"):
			parsed = parse_f4p(FIXTURE)
			doc.update(order_values(parsed))
			doc["f4p_file"] = "f4p.sqlite"
			lines = parsed["material_lines"]
			for pn in parsed["panels"]:
				panels.append(dict(pn, name=f"{doc['name']}/{pn['panel_id']}", production_order=doc["name"]))
		doc["material_lines"] = D.priced_lines(lines)
		if lines:
			doc.update(D.line_costs(doc["material_lines"]))  # demo prices; the sample seal has none
		orders[doc["name"]] = doc

	# --- inventory ----------------------------------------------------------
	items = {i["item_code"]: dict(i, name=i["item_code"]) for i in D.STOCK_ITEMS}
	names = {**{k: c["client_name"] for k, c in clients.items()},
	         **{k: p["project_name"] for k, p in projects.items()},
	         **{k: o["order_title"] for k, o in orders.items()}}
	locations = {D.GENERAL: {"name": D.GENERAL, "scope": "General", "title": location_title("General")}}
	for l in D.LOCATIONS:
		doc = strip_key(l)
		if doc.get("production_order"):
			o = orders[doc["production_order"]]
			doc.update(project=o["project"], client=o["client"])
		elif doc.get("project"):
			doc["client"] = projects[doc["project"]]["client"]
		doc["title"] = location_title(doc["scope"], doc.get("client"), doc.get("project"),
		                              doc.get("production_order"), names=names)
		locations[doc["name"]] = doc

	balances, ledger, movements = {}, [], {}
	for m in D.MOVEMENTS:
		doc = strip_key(m)
		loc_p = locations[doc["location"]].get("project")
		tgt_p = locations.get(doc.get("target_location"), {}).get("project")
		errs = movement_errors(doc["movement_type"], doc["location"], doc.get("target_location"),
		                       doc.get("from_state"), doc["items"], loc_p, tgt_p,
		                       doc.get("is_urgent"), doc.get("reason"))
		legs = movement_legs(doc["movement_type"], doc["location"], doc["items"],
		                     doc.get("target_location"), doc.get("from_state"))
		errs += shortage_errors(legs, lambda *k: balances.get(k, 0))
		if errs:
			raise SystemExit(f"Demo movement {doc['name']} is invalid: {errs}")
		balances = apply_legs(balances, legs)
		if doc["movement_type"] == "Transfer" and needs_urgent_approval(loc_p, tgt_p):
			doc["approver"] = "Administrator"
		for it in doc["items"]:
			it.update(item_name=items[it["stock_item"]]["item_name"], uom=items[it["stock_item"]]["uom"],
			          amount=round(it["qty"] * it["rate"], 2))
		doc.update(docstatus=1, status="Submitted",
		           total_qty=sum(i["qty"] for i in doc["items"]),
		           total_amount=round(sum(i["amount"] for i in doc["items"]), 2))
		movements[doc["name"]] = doc
		for leg in legs:
			loc = locations[leg["location"]]
			ledger.append(dict(leg, name=f"SLE-{len(ledger) + 1:05d}", posting_date=doc["posting_date"],
			                   movement=doc["name"], movement_type=doc["movement_type"],
			                   voucher_type="Stock Movement", is_cancellation=0,
			                   client=loc.get("client"), project=loc.get("project"),
			                   production_order=loc.get("production_order")))

	# --- billing ------------------------------------------------------------
	invoices = {}
	for i in D.INVOICES:
		doc = strip_key(i)
		c = clients[doc["client"]]
		doc.update(client_name=c["client_name"], company_state=D.COMPANY["company_state"],
		           place_of_supply=c["state"])
		res = compute_invoice(doc["items"], doc["company_state"], doc["place_of_supply"])
		for row, amount in zip(doc["items"], res.pop("amounts")):
			row["amount"] = amount
		doc.update(res, docstatus=1)
		invoices[doc["name"]] = doc

	def refresh(inv):
		if inv["invoice_type"] == TAX_INVOICE:
			paid = sum(p["amount"] for p in payments.values() if p["invoice"] == inv["name"])
			credited = sum(n["rounded_total"] for n in invoices.values()
			               if n["invoice_type"] == CREDIT_NOTE and n.get("return_against") == inv["name"])
		else:
			paid = credited = 0
		inv.update(paid_amount=paid, credited_amount=credited,
		           outstanding_amount=outstanding(inv["rounded_total"], paid, credited)
		           if inv["invoice_type"] == TAX_INVOICE else 0,
		           status=invoice_status(1, inv["invoice_type"], inv["rounded_total"], paid, credited,
		                                 inv.get("due_date"), today))

	payments = {}
	for inv in invoices.values():
		refresh(inv)
	for n in [n for n in invoices.values() if n["invoice_type"] == CREDIT_NOTE]:
		orig = invoices[n["return_against"]]
		errs = credit_note_errors(n["rounded_total"], orig["outstanding_amount"], orig["invoice_type"], 1,
		                          orig["client"], n["client"])
		if errs:
			raise SystemExit(f"Demo credit note {n['name']} is invalid: {errs}")
	for p in D.PAYMENTS:
		doc = strip_key(p)
		inv = invoices[doc["invoice"]]
		refresh(inv)
		errs = payment_errors(doc["amount"], inv["outstanding_amount"], inv["invoice_type"], 1,
		                      inv["client"], doc["client"])
		if errs:
			raise SystemExit(f"Demo payment {doc['name']} is invalid: {errs}")
		doc.update(client_name=clients[doc["client"]]["client_name"], docstatus=1, status="Submitted",
		           invoice_outstanding=inv["outstanding_amount"])
		payments[doc["name"]] = doc
	for inv in invoices.values():
		refresh(inv)

	# --- reports ------------------------------------------------------------
	loc_title = {k: v["title"] for k, v in locations.items()}
	stock_rows = {}
	for e in ledger:
		k = (e["location"], e["stock_item"], e["state"])
		stock_rows[k] = stock_rows.get(k, 0) + e["qty_change"]
	stock_balance = pivot_balances(
		[{"location": l, "stock_item": i, "state": s, "qty": q} for (l, i, s), q in stock_rows.items()])
	for r in stock_balance:
		r.update(location_title=loc_title[r["location"]], item_name=items[r["stock_item"]]["item_name"],
		         uom=items[r["stock_item"]]["uom"])
	stock_ledger = running_balances({}, ledger)
	for r in stock_ledger:
		r["location_title"] = loc_title[r["location"]]

	key = {RECEIVED: "received", IN_PROCESS: "in_process", SENT: "sent"}
	material = {}
	for o in orders.values():
		if not o["material_lines"]:
			continue
		stock = {}
		for e in ledger:
			if e["production_order"] == o["name"]:
				s = stock.setdefault(e["stock_item"], {})
				s[key[e["state"]]] = round(s.get(key[e["state"]], 0) + e["qty_change"], 6)
		material[o["name"]] = material_status(o["material_lines"], stock)

	register = []
	for inv in sorted(invoices.values(), key=lambda x: (x["posting_date"], x["name"])):
		row = {k: inv.get(k) for k in ("name", "posting_date", "invoice_type", "status", "client", "client_name",
		                                 "project", "production_order", "due_date", "net_total", "cgst", "sgst",
		                                 "igst", "total_tax", "rounded_total", "paid_amount", "outstanding_amount")}
		if inv["invoice_type"] == CREDIT_NOTE:
			for f in ("net_total", "cgst", "sgst", "igst", "total_tax", "rounded_total", "paid_amount",
			          "outstanding_amount"):
				row[f] = -(row[f] or 0)
		register.append(row)
	ageing = [ageing_row({k: inv.get(k) for k in ("name", "client", "client_name", "project", "posting_date",
	                                              "due_date", "rounded_total", "outstanding_amount")}, today)
	          for inv in sorted(invoices.values(), key=lambda x: x.get("due_date") or "")
	          if inv["invoice_type"] == TAX_INVOICE and inv["outstanding_amount"] > 0]
	order_costs = {}
	for o in orders.values():
		if o["status"] != "Cancelled":
			order_costs[o["project"]] = order_costs.get(o["project"], 0) + (o.get("cost_grand") or 0)
	billing = project_summary([i for i in invoices.values() if i["invoice_type"] in (TAX_INVOICE, CREDIT_NOTE)],
	                          order_costs)
	for r in billing:
		r.update(project_name=projects[r["project"]]["project_name"], client=projects[r["project"]]["client"])

	return {
		"meta": {"today": today, "company": D.COMPANY, "commit": _commit()},
		"docs": {
			"Cabinet Client": list(clients.values()),
			"Cabinet Project": list(projects.values()),
			"Production Order": list(orders.values()),
			"Order Panel": panels,
			"Stock Item": list(items.values()),
			"Stock Location": list(locations.values()),
			"Stock Movement": list(movements.values()),
			"Stock Ledger Entry": ledger,
			"Cabinet Invoice": list(invoices.values()),
			"Payment Entry Lite": list(payments.values()),
		},
		"reports": {
			"Stock Balance": stock_balance,
			"Stock Ledger": stock_ledger,
			"Order Material Status": material,
			"Invoice Register": register,
			"Receivables Ageing": ageing,
			"Project Billing Summary": billing,
		},
	}


def _commit():
	try:
		return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
	except Exception:
		return ""


if __name__ == "__main__":
	out = os.path.join(ROOT, "site", "data.json")
	data = build()
	with open(out, "w") as f:
		json.dump(data, f, indent=1, default=str)
	counts = {k: len(v) for k, v in data["docs"].items()}
	print(f"wrote {out}: {counts}")
