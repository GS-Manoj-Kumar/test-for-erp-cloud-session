"""Helpers for the PDF / print templates. Pure Python (no Frappe imports), so the same
templates can be rendered by Frappe (Print Formats) and by the static demo build.

The templates in cabinet_erp/templates/print/ only use `p` (the dict built here) and the
filters in FILTERS.
"""

import datetime as dt
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

PAISA = Decimal("0.01")

INVOICE_TITLES = {
	"Tax Invoice": "TAX INVOICE",
	"Proforma": "PROFORMA INVOICE",
	"Quotation": "QUOTATION",
	"Credit Note": "CREDIT NOTE",
}

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
         "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _d(x):
	return Decimal(str(x or 0))


# --- formatting -------------------------------------------------------------

def inr(value, symbol=False):
	"""Indian digit grouping: 1234567.5 -> '12,34,567.50'."""
	q = _d(value).quantize(PAISA, rounding=ROUND_HALF_UP)
	sign = "-" if q < 0 else ""
	whole, frac = f"{abs(q):.2f}".split(".")
	if len(whole) > 3:
		head, tail = whole[:-3], whole[-3:]
		groups = []
		while len(head) > 2:
			groups.insert(0, head[-2:])
			head = head[:-2]
		if head:
			groups.insert(0, head)
		whole = ",".join(groups + [tail])
	return f"{sign}{'₹' if symbol else ''}{whole}.{frac}"


def qty(value):
	"""Quantities: drop trailing zeros (8.0 -> '8', 2.394 -> '2.394')."""
	q = _d(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP).normalize()
	return f"{q:f}"


def fdate(value):
	"""'2026-11-03' -> '03-11-2026' (the usual Indian invoice date style)."""
	if not value:
		return ""
	if not isinstance(value, (dt.date, dt.datetime)):
		value = dt.date.fromisoformat(str(value)[:10])
	return value.strftime("%d-%m-%Y")


def _words_below_1000(n):
	words = []
	if n >= 100:
		words += [_ONES[n // 100], "Hundred"]
		n %= 100
	if n >= 20:
		words.append(_TENS[n // 10])
		n %= 10
	if n:
		words.append(_ONES[n])
	return words


def number_in_words(n):
	"""Indian system: 1,04,000 -> 'One Lakh Four Thousand'."""
	n = int(n)
	if n == 0:
		return "Zero"
	words = []
	for unit, size in (("Crore", 10 ** 7), ("Lakh", 10 ** 5), ("Thousand", 10 ** 3)):
		if n >= size:
			# crores can exceed 99; spell them out recursively
			words += (number_in_words(n // size).split() if unit == "Crore" else _words_below_1000(n // size))
			words.append(unit)
			n %= size
	words += _words_below_1000(n)
	return " ".join(words)


def rupees_in_words(amount):
	q = _d(amount).quantize(PAISA, rounding=ROUND_HALF_UP)
	sign = "Minus " if q < 0 else ""
	q = abs(q)
	rupees, paise = int(q), int((q - int(q)) * 100)
	text = f"{sign}Rupees {number_in_words(rupees)}"
	if paise:
		text += f" and {number_in_words(paise)} Paise"
	return text + " Only"


# --- GST summary ------------------------------------------------------------

def gst_summary(items, inter_state):
	"""Tax per GST rate, rounded the same way as billing_logic.compute_invoice."""
	by_rate = OrderedDict()
	for it in items:
		rate = int(_d(it.get("gst_rate")))
		amount = (_d(it.get("qty")) * _d(it.get("rate"))).quantize(PAISA, rounding=ROUND_HALF_UP)
		by_rate[rate] = by_rate.get(rate, Decimal(0)) + amount
	rows = []
	for rate in sorted(by_rate):
		base = by_rate[rate]
		if inter_state:
			igst = (base * rate / 100).quantize(PAISA, rounding=ROUND_HALF_UP)
			cgst = sgst = Decimal(0)
		else:
			cgst = sgst = (base * rate / 200).quantize(PAISA, rounding=ROUND_HALF_UP)
			igst = Decimal(0)
		rows.append({"rate": rate, "half_rate": rate / 2, "taxable": float(base), "cgst": float(cgst),
		             "sgst": float(sgst), "igst": float(igst), "total_tax": float(cgst + sgst + igst)})
	return rows


# --- context for each print format -------------------------------------------

def print_context(doctype, doc, company=None, client=None, extra=None):
	"""Everything a template needs. `doc` is a plain dict (child tables as lists of dicts)."""
	company = company or {}
	p = {"doc": doc, "company": company, "client": client or {}, "doctype": doctype}
	p.update(extra or {})
	if doctype == "Cabinet Invoice":
		p["title"] = INVOICE_TITLES.get(doc.get("invoice_type"), "INVOICE")
		p["inter_state"] = bool(doc.get("is_inter_state"))
		p["gst_rows"] = gst_summary(doc.get("items") or [], p["inter_state"])
		p["amount_in_words"] = rupees_in_words(doc.get("rounded_total"))
		p["show_payment"] = doc.get("invoice_type") == "Tax Invoice" and doc.get("docstatus") == 1
	elif doctype == "Payment Entry Lite":
		p["title"] = "PAYMENT RECEIPT"
		p["amount_in_words"] = rupees_in_words(doc.get("amount"))
	elif doctype == "Production Order":
		p["title"] = "PRODUCTION CUTLIST"
		panels = p.get("panels") or []
		p["panel_total_qty"] = sum(int(x.get("quantity") or 0) for x in panels)
		p["panel_total_area_m2"] = round(sum(float(x.get("area") or 0) * int(x.get("quantity") or 1)
		                                     for x in panels) / 1_000_000, 3)
		groups = OrderedDict()
		for x in panels:
			groups.setdefault(x.get("material_name") or "-", 0)
			groups[x.get("material_name") or "-"] += int(x.get("quantity") or 0)
		p["panel_groups"] = [{"material": k, "qty": v} for k, v in groups.items()]
	elif doctype == "Stock Movement":
		mt = doc.get("movement_type")
		p["title"] = "DELIVERY CHALLAN" if mt in ("Dispatch", "Transfer") else "STOCK MOVEMENT"
	return p


# Prefixed names used as Jinja filters (registered in hooks.py), so they can't clash
# with Frappe's own filters.
def cab_inr(value):
	return inr(value)


def cab_qty(value):
	return qty(value)


def cab_date(value):
	return fdate(value)


FILTERS = {"cab_inr": cab_inr, "cab_qty": cab_qty, "cab_date": cab_date}
