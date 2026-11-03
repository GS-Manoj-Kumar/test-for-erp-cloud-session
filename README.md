# Cabinet ERP

CRM + Inventory + Invoices for a CNC cabinet-production business, built as a
Frappe v15 app (`cabinet_erp`). See `CLAUDE.md` for the full spec and the phase plan.

[![Tests](https://github.com/GS-Manoj-Kumar/test-for-erp-cloud-session/actions/workflows/tests.yml/badge.svg)](https://github.com/GS-Manoj-Kumar/test-for-erp-cloud-session/actions/workflows/tests.yml)
[![Open live app in Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/GS-Manoj-Kumar/test-for-erp-cloud-session?quickstart=1)

**Demo (dummy data, read-only):** https://gs-manoj-kumar.github.io/test-for-erp-cloud-session/

Hierarchy: **Client (C0001)** → **Project (P0001)** → **Production Order (P0001-ORD-01)**.

## Status

| Phase | What | State |
|---|---|---|
| 1 | Scaffold, Cabinet Client, Cabinet Project | done |
| 2 | Production Order + F4P import | done |
| 3 | Inventory | done |
| 4 | Billing | done |
| 5 | CRM glue, roles, workspace | – |

## Demo and live preview

| | What it is | How |
|---|---|---|
| **Demo site** | Static, read-only pages on GitHub Pages: clients, projects, orders (88 imported panels), stock, invoices, all six reports. The data is made up, but every total is computed by the app's own Python code. | Open the link above. Rebuilt on every push to `main` by `.github/workflows/pages.yml`. Local: `python scripts/build_demo_site.py && python -m http.server -d site 8080` |
| **Live preview** | The real app (Frappe v15 + CRM + cabinet_erp) running in a GitHub Codespace with the same demo data loaded. You can create and submit records. | Click the Codespaces badge above. First start takes 10–15 min, then port 8000 opens; log in as `Administrator` / `admin`. See `.devcontainer/README.md`. |

The demo data lives in `cabinet_erp/demo_data.py` and is used by both. To load it into
any fresh site: `bench --site <site> execute cabinet_erp.demo.setup_demo`.

## Local install

Needs a working Frappe v15 bench (Python 3.10+, MariaDB, Redis, Node 18+).

```bash
cd ~/frappe-bench
bench get-app crm --branch main            # Frappe CRM (required app)
bench get-app https://github.com/GS-Manoj-Kumar/test-for-erp-cloud-session --branch <branch>
bench new-site cabinet.localhost           # skip if you already have a site
bench --site cabinet.localhost install-app crm
bench --site cabinet.localhost install-app cabinet_erp
bench --site cabinet.localhost migrate
bench start
```

Then open http://cabinet.localhost:8000/app/cabinet-client.

Updating after pulling new commits:

```bash
cd ~/frappe-bench/apps/cabinet_erp && git pull
bench --site cabinet.localhost migrate
```

## Tests

Pure-Python tests (no bench needed):

```bash
pip install pytest
python -m pytest
```

Integration tests inside a bench:

```bash
bench --site cabinet.localhost run-tests --app cabinet_erp
```

Check every doctype JSON parses:

```bash
find cabinet_erp -name '*.json' -exec python -m json.tool {} \; > /dev/null
```

## Layout

```
cabinet_erp/            Frappe app package
  hooks.py, modules.txt
  clients/doctype/      Cabinet Client, Cabinet Project
  production/doctype/   Production Order, Order Panel, Order Material Line
  production/f4p_import.py   pure-Python f4p.sqlite parser (parse_f4p)
  inventory/doctype/    Stock Item, Stock Location, Stock Movement, Stock Ledger Entry
  inventory/report/     Stock Balance, Stock Ledger, Order Material Status
  inventory/stock_logic.py   pure-Python balance / transfer rules
  billing/doctype/      Cabinet Settings, Cabinet Invoice, Cabinet Invoice Item, Payment Entry Lite
  billing/report/       Invoice Register, Receivables Ageing, Project Billing Summary
  billing/billing_logic.py   pure-Python GST / outstanding / status rules
  utils/gst.py          pure-Python GSTIN helpers
  demo_data.py, demo.py dummy dataset + loader for a real site
tests/                  plain-pytest suite + fixtures/f4p.sqlite
site/, scripts/         static demo site (GitHub Pages) and its data builder
.devcontainer/          Codespaces live preview (bench + MariaDB + Redis)
.github/workflows/      tests on every push/PR; Pages deploy on main
DECISIONS.md            choices made where the spec was open
```

## Importing an F4P seal

Open a Production Order → **Import F4P** → upload the sealed `f4p.sqlite` → **Import**.
Re-importing the same seal does nothing; a newer seal replaces the order's panels and
material lines. Panels are listed under **View → Panels**.

## Stock

Stock only changes through a submitted **Stock Movement**. Pick a **Stock Location** (General
Store, or one per client / project / order), then one of:

| Movement | Effect (same location unless noted) |
|---|---|
| Receipt | + Received |
| Issue to Production | Received → In Process |
| Return from Production | In Process → Received |
| Dispatch | Received or In Process → Sent |
| Transfer | Received at A → Received at B (project → other project needs Urgent + Reason) |

Cancelling a movement writes reversing ledger rows; ledger rows are never edited or deleted.
Reports: **Stock Balance**, **Stock Ledger**, **Order Material Status** (map Order Material
Lines to Stock Items first).

## Billing

First set **Cabinet Settings → Company State** (and GSTIN). Invoices use it to choose
CGST + SGST (same state as the place of supply) or IGST (other state).

- **Cabinet Invoice** types: Quotation, Proforma, Tax Invoice, Credit Note. Only a Tax Invoice
  carries an outstanding amount; the others show status *Issued*.
- On a draft invoice with an order selected, **Make from Order** fills items from the order's
  material lines or adds one lump-sum line at the order cost. Production Order → **Create →
  Invoice** starts one prefilled.
- Record money with **Payment Entry Lite** (Tax Invoice → Create → Payment). A **Credit Note**
  against a Tax Invoice reduces its outstanding.
- Overdue status is updated by a daily scheduler job (`bench enable-scheduler`).
