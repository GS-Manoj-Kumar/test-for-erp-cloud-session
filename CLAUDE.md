# CLAUDE.md — Cabinet ERP (CRM + Inventory + Invoices) on Frappe

Read this whole file before doing anything. It is the spec and the rules.

## 0. Budget rules (the owner is on limited free credits)

- Work on ONE phase per session (see section 6). When the phase's checklist is done,
  commit, push, open the PR, write a short summary, and STOP. Do not start the next phase.
- Do NOT install or run a full Frappe bench / MariaDB / Redis in this VM unless the task
  explicitly says so. The owner tests locally. Write code, JSON doctypes, and pure-Python
  unit tests that run with plain `pytest` (no bench needed).
- Do not explore aimlessly. Read only the files you need. No large refactors outside the phase.
- No frontend frameworks beyond what Frappe Desk gives. Use standard Desk forms, list views,
  report views and Script Reports. No custom Vue/React UI in v1.
- If something in this spec is ambiguous, pick the simplest reasonable option, note it in
  `DECISIONS.md`, and keep going. Do not stop to ask.

## 1. What this is

A small ERP for a CNC cabinet-production business. It replaces the "managing" side of an
existing PyQt5 desktop app. Production data per order comes from a sealed SQLite file
(`f4p.sqlite`, schema_version 7) produced by the F4P pipeline (`sealer.py`).

Hierarchy (strict):

    Client (B2B or B2C)
      └── Project (0..n per client)
            └── Production Order (0..n per project)
                  └── order data: panels, material requirements, costs (imported from f4p.sqlite)

Three modules:
1. **CRM** — behave like Frappe CRM (leads → deals → client), lightly customised.
2. **Invoices** — like Frappe/ERPNext sales invoices but lean: invoice per client, optionally
   tagged to project and order; payments; status; filters by date / client / project / order.
3. **Inventory** — simple stock ledger scoped per client, per project or per order, with
   received / in-process / sent states and project-to-project transfer for urgent jobs.

## 2. Stack and repo layout

- Frappe Framework v15. Custom app name: `cabinet_erp`.
- Depends on the Frappe CRM app (`crm`) for leads/deals/contacts/organizations.
  Do NOT depend on ERPNext (too heavy for this use).
- Python 3.10+. Indian context: currency INR, GST (CGST+SGST intra-state, IGST inter-state).

```
cabinet_erp/
  cabinet_erp/
    hooks.py
    modules.txt                # Clients, Inventory, Billing, Production
    clients/doctype/...        # Cabinet Client, Cabinet Project
    production/doctype/...     # Production Order, Order Panel, Order Material Line
    inventory/doctype/...      # Stock Item, Stock Location, Stock Movement, Stock Ledger Entry
    billing/doctype/...        # Cabinet Invoice, Cabinet Invoice Item, Payment Entry Lite
    production/f4p_import.py   # pure-Python parser + Frappe glue (kept separate)
    report/...                 # Script Reports
  tests/
    fixtures/f4p.sqlite        # sample sealed DB (provided by owner)
    test_f4p_parser.py         # runs with plain pytest, no bench
  DECISIONS.md
  README.md                    # local install: bench get-app, install-app, migrate
```

## 3. Doctypes

Naming follows the existing NAS engine conventions: clients `C0001`, projects `P0001`
(global counters, zero-padded 4 digits), orders `<project_id>-ORD-01`, `-ORD-02` …

### Clients module
**Cabinet Client** (naming `C.####`)
- client_name, client_type (Select: B2B, B2C), crm_organization (Link CRM Organization,
  optional for B2C), primary_contact (Link Contact), phone, email
- gstin (B2B only, validate 15-char format), billing_address, shipping_address, state (for GST)
- Hook: when a CRM Deal is marked Won, offer to create/link a Cabinet Client.

**Cabinet Project** (naming `P.####`)
- client (Link Cabinet Client, required), project_name, project_type (B2B/B2C, default from
  client), property_type, assigned_designer, assigned_pm (Link User)
- milestone (Select: Enquiry, Token Booked, Advance Paid, Design, Confirmed, Production,
  Dispatched, Installed, Handover, Closed). Default Enquiry.
- dates: token_booking, advance_paid, confirmation, target_handover, estimated_handover,
  actual_handover
- nas_path (Data) — path of the project folder on the NAS; display only, no file ops in v1.

### Production module
**Production Order** (naming `{project}-ORD-{##}`)
- project (Link, required), client (fetched from project, read-only), order_title,
  status (Draft, Released, Cutting, Edge Banding, Packed, Dispatched, Delivered, Cancelled)
- f4p fields (read-only, filled by import): seal_id, sealed_at, sealer_version, skp_name,
  panel_count, variety_count, sheet_count, f4p_file (Attach)
- cost fields from `cost_total`: cost_core, cost_laminate, cost_glue, cost_edge_band, cost_grand
- child table **Order Material Line**: kind (core/laminate/glue/edge_band), description,
  size, qty, order_qty, wastage_pct, unit_price, line_total, stock_item (Link, mapped later)
- **Order Panel** is a separate doctype (not a child table; orders can have hundreds of
  panels): order (Link), panel_id, panel_index, quantity, code_name_1..3, shape_type,
  thickness, material_name, finished_length, finished_width, area, grain,
  edge_band_summary, sheet_index, board_index, pack_group (from `pack_item.group_code`),
  exclusion_status, warnings.

### Inventory module
**Stock Item**: item_code, item_name, kind (core sheet, laminate, edge band, glue, hardware,
other), uom (Sheet, m, kg, Nos), thickness, size_label, color, default_rate.

**Stock Location** (where stock is "booked"): scope (Select: General, Client, Project,
Order), client / project / order (Links, required according to scope), title auto-built.
One General store location exists by default.

**Stock Movement** (submittable; the only way stock changes)
- movement_type (Select):
  - Receipt — from supplier into a location (state Received)
  - Issue to Production — Received → In Process (same location)
  - Return from Production — In Process → Received
  - Dispatch — In Process or Received → Sent (finished goods out to client)
  - Transfer — location A → location B (state Received). If both are projects, require
    `is_urgent` checkbox + `reason` text and record approver = session user.
- posting_date, remarks, child table of items (stock_item, qty, rate).
- On submit, write **Stock Ledger Entry** rows (append-only): posting_date, stock_item,
  location, state (Received / In Process / Sent), qty_change (+/-), movement (Link),
  voucher_type. On cancel, write reversing rows. Never update or delete ledger rows.
- Validation: cannot take more out of a (location, state, item) than its balance.

**Reports** (Script Reports):
- Stock Balance — filters: client, project, order, item, state; groups by location.
- Stock Ledger — same filters + date range.
- Order Material Status — for one order: required (from Order Material Lines) vs received
  vs in process vs sent, and shortfall.

### Billing module
**Cabinet Invoice** (submittable, naming `INV-.YY.-.####`)
- client (required), project (optional, filtered by client), production_order (optional,
  filtered by project), invoice_type (Quotation, Proforma, Tax Invoice, Credit Note)
- posting_date, due_date, place_of_supply (state)
- items child (**Cabinet Invoice Item**): description, hsn_sac, qty, uom, rate, amount,
  gst_rate (0/5/12/18/28)
- totals: net_total, cgst, sgst, igst (computed: same state → CGST+SGST, else IGST),
  grand_total, rounded_total, paid_amount, outstanding_amount
- status: Draft, Unpaid, Partly Paid, Paid, Overdue (Overdue computed daily by scheduler),
  Cancelled
- Button "Make from Order": prefill items from the order's material lines or a single
  lump-sum line.

**Payment Entry Lite** (submittable): client, invoice (Link), posting_date, amount, mode
(Cash, UPI, NEFT/RTGS, Cheque), reference_no. On submit/cancel update invoice paid/outstanding.

**Reports**: Invoice Register (filters: date range, client, project, order, status,
invoice_type; shows totals row), Receivables Ageing (0-30, 31-60, 61-90, 90+), Project
Billing Summary (per project: invoiced, paid, outstanding, order cost_grand, margin).

## 4. f4p.sqlite import (Production Order → button "Import F4P")

`f4p_import.py` must have a pure-Python function `parse_f4p(path) -> dict` with no Frappe
imports, so it is testable with pytest against `tests/fixtures/f4p.sqlite`.

Source tables in the sealed DB (read-only; open with `sqlite3` URI `mode=ro`):
- `meta` (key/value): seal_id, sealed_at, sealer_version, skp_name, schema_version,
  panel_count, variety_count, project_code, client_code, order_no
- `panel` (88 rows in fixture) and view `v_mastercutlist` (adds sheet_index, board_index)
- `pack_item` (panel_id → group_code)
- `material_cost` (kind, description, size, qty, order_qty, wastage_pct, unit_price, line_total)
- `cost_total` (kind → amount; ignore keys starting with `_`)
- `sheet` (count rows for sheet_count)

Rules:
- Refuse if schema_version != 7 (clear error message with the found version).
- Idempotent: if the order already has the same seal_id, do nothing. If a different
  seal_id, replace that order's panels and material lines (latest seal wins, same as sealer).
- `meta.project_code` / `client_code` / `order_no` may be empty or `NO_PROJECT` in old seals:
  never trust them over the order the user is importing into; just warn if they disagree.
- Descriptions in `material_cost` may have leading spaces: strip them.

Tests (pytest, no bench): schema check, panel count = 88 on fixture, material lines = 12,
cost keys parsed, idempotency key = seal_id.

## 5. Permissions (simple)
Roles: Cabinet Admin (all), Sales (CRM + clients + projects + invoices read/write),
Production (orders + stock movements), Accounts (invoices + payments + reports).

## 6. Phases (one per session)

1. **Scaffold**: app skeleton, hooks, modules, Cabinet Client, Cabinet Project, naming
   series, README with local install steps, DECISIONS.md. Validate all doctype JSONs load.
2. **Production + import**: Production Order, Order Panel, Order Material Line,
   `parse_f4p` + pytest suite + Import F4P button.
3. **Inventory**: Stock Item, Stock Location, Stock Movement, Stock Ledger Entry, balance
   validation, the three stock reports. Unit-test the balance/transfer logic as plain Python.
4. **Billing**: Cabinet Invoice, items, GST calc, Payment Entry Lite, overdue scheduler,
   three billing reports. Unit-test GST and outstanding calc as plain Python.
5. **CRM glue + roles**: Deal Won → Client hook, permissions, workspace page with shortcuts.

Each phase ends with: all pytest green, `python -m json.tool` passes on every doctype JSON,
PR opened with a checklist of what to test locally.

## 7. Out of scope for v1
NAS file management (folder creation, copy, trash), label printing, packing, DXF/CNC files,
e-invoicing/IRN, multi-currency, purchase orders, supplier management beyond a text field.
