# Cabinet ERP

CRM + Inventory + Invoices for a CNC cabinet-production business, built as a
Frappe v15 app (`cabinet_erp`). See `CLAUDE.md` for the full spec and the phase plan.

Hierarchy: **Client (C0001)** → **Project (P0001)** → **Production Order (P0001-ORD-01)**.

## Status

| Phase | What | State |
|---|---|---|
| 1 | Scaffold, Cabinet Client, Cabinet Project | done |
| 2 | Production Order + F4P import | done |
| 3 | Inventory | – |
| 4 | Billing | – |
| 5 | CRM glue, roles, workspace | – |

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
  inventory/ billing/   (filled in later phases)
  utils/gst.py          pure-Python GSTIN helpers
tests/                  plain-pytest suite + fixtures/f4p.sqlite
DECISIONS.md            choices made where the spec was open
```

## Importing an F4P seal

Open a Production Order → **Import F4P** → upload the sealed `f4p.sqlite` → **Import**.
Re-importing the same seal does nothing; a newer seal replaces the order's panels and
material lines. Panels are listed under **View → Panels**.
