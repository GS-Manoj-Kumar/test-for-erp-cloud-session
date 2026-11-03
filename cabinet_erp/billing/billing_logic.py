"""Billing rules as plain Python (NO Frappe imports) so they can be unit-tested with pytest.

Money is computed with Decimal and returned as floats rounded to 2 places (paise).
"""

import datetime as dt
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

GST_RATES = (0, 5, 12, 18, 28)

QUOTATION = "Quotation"
PROFORMA = "Proforma"
TAX_INVOICE = "Tax Invoice"
CREDIT_NOTE = "Credit Note"
INVOICE_TYPES = (QUOTATION, PROFORMA, TAX_INVOICE, CREDIT_NOTE)
# only these can be paid / chase money; the rest are "Issued" documents
RECEIVABLE_TYPES = (TAX_INVOICE,)

DRAFT, ISSUED, UNPAID, PARTLY_PAID, PAID, OVERDUE, CANCELLED = (
	"Draft", "Issued", "Unpaid", "Partly Paid", "Paid", "Overdue", "Cancelled")

AGEING_BUCKETS = (("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("90+", 91, None))

PAISA = Decimal("0.01")
RUPEE = Decimal("1")


class BillingError(ValueError):
	pass


def D(x):
	return Decimal(str(x or 0))


def money(x):
	return float(D(x).quantize(PAISA, rounding=ROUND_HALF_UP))


def _date(x):
	if x is None or isinstance(x, dt.date):
		return x
	return dt.date.fromisoformat(str(x)[:10])


# --- GST --------------------------------------------------------------------

def is_inter_state(company_state, place_of_supply):
	"""IGST when supply goes to another state. Unknown place of supply = same state."""
	return bool(company_state and place_of_supply and company_state != place_of_supply)


def compute_invoice(items, company_state, place_of_supply):
	"""items: [{qty, rate, gst_rate}]. Returns line amounts and totals.

	Tax is computed per GST rate group (sum of amounts x rate) and rounded to paise.
	Intra-state: CGST = SGST = half the rate each, each rounded separately, so they are
	always equal. Inter-state: IGST = full rate. rounded_total is the nearest rupee.
	"""
	inter = is_inter_state(company_state, place_of_supply)
	amounts, by_rate = [], OrderedDict()
	for i, it in enumerate(items, 1):
		rate = int(D(it.get("gst_rate")))
		if rate not in GST_RATES:
			raise BillingError(f"Row {i}: GST rate {rate}% is not one of {GST_RATES}.")
		amount = (D(it.get("qty")) * D(it.get("rate"))).quantize(PAISA, rounding=ROUND_HALF_UP)
		amounts.append(float(amount))
		by_rate[rate] = by_rate.get(rate, Decimal(0)) + amount

	cgst = sgst = igst = Decimal(0)
	for rate, base in by_rate.items():
		if inter:
			igst += (base * rate / 100).quantize(PAISA, rounding=ROUND_HALF_UP)
		else:
			half = (base * rate / 200).quantize(PAISA, rounding=ROUND_HALF_UP)
			cgst += half
			sgst += half

	net = sum(by_rate.values(), Decimal(0))
	tax = cgst + sgst + igst
	grand = net + tax
	rounded = grand.quantize(RUPEE, rounding=ROUND_HALF_UP)
	return {
		"amounts": amounts,
		"is_inter_state": int(inter),
		"net_total": float(net),
		"cgst": float(cgst),
		"sgst": float(sgst),
		"igst": float(igst),
		"total_tax": float(tax),
		"grand_total": float(grand),
		"rounding_adjustment": float(rounded - grand),
		"rounded_total": float(rounded),
	}


# --- outstanding & status ---------------------------------------------------

def outstanding(rounded_total, paid_amount=0, credited_amount=0):
	return money(D(rounded_total) - D(paid_amount) - D(credited_amount))


def invoice_status(docstatus, invoice_type, rounded_total, paid_amount=0, credited_amount=0,
                   due_date=None, today=None):
	"""Overdue wins over Partly Paid / Unpaid once the due date has passed."""
	if docstatus == 0:
		return DRAFT
	if docstatus == 2:
		return CANCELLED
	if invoice_type not in RECEIVABLE_TYPES:
		return ISSUED
	out = outstanding(rounded_total, paid_amount, credited_amount)
	if out <= 0:
		return PAID
	today = _date(today) or dt.date.today()
	if due_date and _date(due_date) < today:
		return OVERDUE
	if D(paid_amount) + D(credited_amount) > 0:
		return PARTLY_PAID
	return UNPAID


def payment_errors(amount, invoice_outstanding, invoice_type=TAX_INVOICE, invoice_docstatus=1,
                   invoice_client=None, client=None):
	errors = []
	if invoice_docstatus != 1:
		errors.append("Invoice must be submitted before it can be paid.")
	if invoice_type not in RECEIVABLE_TYPES:
		errors.append(f"Only a {TAX_INVOICE} can be paid (this is a {invoice_type}).")
	if invoice_client and client and invoice_client != client:
		errors.append(f"Invoice belongs to client {invoice_client}, not {client}.")
	if D(amount) <= 0:
		errors.append("Amount must be greater than 0.")
	elif D(amount) > D(invoice_outstanding):
		errors.append(f"Amount {money(amount):.2f} is more than the outstanding {money(invoice_outstanding):.2f}.")
	return errors


def credit_note_errors(credit_total, original_outstanding, original_type, original_docstatus,
                       original_client=None, client=None):
	errors = []
	if original_docstatus != 1 or original_type != TAX_INVOICE:
		errors.append("A Credit Note must be against a submitted Tax Invoice.")
	if original_client and client and original_client != client:
		errors.append(f"Original invoice belongs to client {original_client}, not {client}.")
	if D(credit_total) <= 0:
		errors.append("Credit Note total must be greater than 0.")
	elif D(credit_total) > D(original_outstanding):
		errors.append(
			f"Credit {money(credit_total):.2f} is more than the invoice's outstanding {money(original_outstanding):.2f}.")
	return errors


# --- Make from Order --------------------------------------------------------

KIND_UOM = {"core": "Sheet", "laminate": "Sheet", "edge_band": "m", "glue": "kg"}
KIND_LABEL = {"core": "Core", "laminate": "Laminate", "edge_band": "Edge band", "glue": "Glue"}


def order_invoice_items(order, lines, mode="lines", gst_rate=18):
	"""Invoice rows for a Production Order.

	mode 'lines': one row per material line (qty = order_qty, rate = unit_price).
	mode 'lump_sum': one row for the whole order at its cost_grand.
	"""
	if mode == "lump_sum":
		title = order.get("order_title") or ""
		return [{
			"description": f"Production order {order['name']}" + (f" - {title}" if title else ""),
			"qty": 1, "uom": "Nos", "rate": money(order.get("cost_grand")), "gst_rate": gst_rate,
		}]
	if mode != "lines":
		raise BillingError(f"Unknown mode {mode!r}.")
	rows = []
	for l in lines:
		kind = l.get("kind") or ""
		parts = [KIND_LABEL.get(kind, kind.title()), l.get("description") or "", l.get("size") or ""]
		rows.append({
			"description": " ".join(p for p in parts if p).strip(),
			"qty": float(D(l.get("order_qty") or l.get("qty"))),
			"uom": KIND_UOM.get(kind, "Nos"),
			"rate": money(l.get("unit_price")),
			"gst_rate": gst_rate,
		})
	return rows


# --- reports ----------------------------------------------------------------

def ageing_bucket(days_overdue):
	for label, lo, hi in AGEING_BUCKETS:
		if days_overdue >= lo and (hi is None or days_overdue <= hi):
			return label
	return AGEING_BUCKETS[0][0]  # not yet due counts as 0-30


def ageing_row(invoice, as_of):
	"""invoice: {due_date, posting_date, outstanding_amount, ...}. Days are counted from the
	due date (posting date if no due date). Not-yet-due invoices land in 0-30."""
	ref = _date(invoice.get("due_date") or invoice.get("posting_date"))
	days = max((_date(as_of) - ref).days, 0)
	row = dict(invoice, days_overdue=days)
	for label, _, _ in AGEING_BUCKETS:
		row[bucket_field(label)] = 0.0
	row[bucket_field(ageing_bucket(days))] = money(invoice.get("outstanding_amount"))
	return row


def bucket_field(label):
	return "b_" + label.replace("-", "_").replace("+", "_plus")


def project_summary(invoices, order_costs):
	"""invoices: [{project, invoice_type, net_total, rounded_total, paid_amount, outstanding_amount}]
	(submitted Tax Invoices and Credit Notes only). order_costs: {project: total cost_grand}.
	Credit Notes reduce invoiced. Margin = invoiced (excl. GST) - order cost."""
	acc = OrderedDict()

	def row(p):
		return acc.setdefault(p, {"project": p, "invoiced": Decimal(0), "invoiced_net": Decimal(0),
		                          "paid": Decimal(0), "outstanding": Decimal(0), "order_cost": Decimal(0)})

	for inv in invoices:
		if not inv.get("project"):
			continue
		r = row(inv["project"])
		sign = -1 if inv["invoice_type"] == CREDIT_NOTE else 1
		r["invoiced"] += sign * D(inv.get("rounded_total"))
		r["invoiced_net"] += sign * D(inv.get("net_total"))
		if inv["invoice_type"] == TAX_INVOICE:
			r["paid"] += D(inv.get("paid_amount"))
			r["outstanding"] += D(inv.get("outstanding_amount"))
	for p, cost in order_costs.items():
		row(p)["order_cost"] += D(cost)

	out = []
	for p in sorted(acc):
		r = acc[p]
		margin = r["invoiced_net"] - r["order_cost"]
		pct = (margin / r["invoiced_net"] * 100) if r["invoiced_net"] else Decimal(0)
		out.append({"project": p, **{k: money(r[k]) for k in ("invoiced", "invoiced_net", "paid",
		                                                        "outstanding", "order_cost")},
		            "margin": money(margin), "margin_pct": money(pct)})
	return out
