# Decisions

Choices made where `CLAUDE.md` left room. Newest phase last.

## Phase 1 — Scaffold

1. **Repo root = app root.** The spec draws `cabinet_erp/cabinet_erp/...`; here the repo
   itself is the outer `cabinet_erp/` folder, so `bench get-app <repo-url>` works directly.
2. **Naming.** `autoname` = `C.####` / `P.####` (Frappe "Expression (old style)"), giving
   `C0001`, `P0001`. Counters are per-doctype in `tabSeries`. Existing NAS ids are not
   imported in v1; if migrating, set the `C` / `P` series start in Naming Series settings.
3. **GSTIN validation** = 15-char regex + official base-36 check digit + known state code.
   Lives in `cabinet_erp/utils/gst.py` (no Frappe import) so it is unit-tested with pytest.
4. **GSTIN on B2C clients is cleared** on save rather than raising an error (the field is
   hidden for B2C, so a stale value would otherwise be invisible).
5. **State** is a Select of Indian states/UTs (needed for CGST+SGST vs IGST later). If left
   empty on a B2B client it is filled from the GSTIN's state code; a mismatch only warns.
6. **Addresses** are plain Small Text fields (as the spec lists), not Frappe Address
   documents. Keeps v1 simple; can move to Address links later.
7. **property_type** is free text (Data), matching the NAS app, which also stores it as text.
8. **project_type** defaults from the client's type (in the form and again on save if empty).
9. **Date sanity checks** on Project: Advance Paid ≥ Token Booking, Actual Handover ≥
   Confirmation. Nothing else is enforced.
10. **Permissions** are System Manager only for now. The four roles (Cabinet Admin, Sales,
    Production, Accounts) come in Phase 5 as fixtures, so doctype JSON never references a
    role that does not exist yet.
11. **`required_apps = ["crm"]`** in hooks, since Cabinet Client links to `CRM Organization`.
12. **Fixture** `tests/fixtures/f4p.sqlite` (schema 7, 88 panels, 12 material lines) is
    committed now so Phase 2 can use it.
13. Bench-only tests (`test_cabinet_*.py` inside doctype folders) are kept out of the plain
    pytest run via `testpaths = ["tests"]`.

## Phase 2 — Production + import

14. **Order Panel's link field is `production_order`, not `order`.** `order` is a reserved
    SQL word and would need quoting in every raw query and report.
15. **`stock_item` on Order Material Line is deferred to Phase 3.** Frappe refuses a Link to
    a doctype that does not exist yet (Stock Item), so the field comes with Inventory.
16. **Production Order naming** = `format:{project}-ORD-{##}` → `P0001-ORD-01`. The counter
    is per project.
17. **Where the code lives:** `production/f4p_import.py` is pure Python (parse, plan, warn,
    map). The Frappe side is the whitelisted `ProductionOrder.import_f4p(file_url)` doc method,
    which the **Import F4P** button calls.
18. **Upload flow:** the button opens a dialog that uploads the file as a Frappe File. The
    import then attaches it to the order and stores the URL in `f4p_file`.
19. **Replace = delete + re-insert** the order's Order Panels and material lines in the
    same request (one DB transaction). Panels use random (hash) names.
20. **Panel placement:** `sheet_index` / `board_index` come from `v_mastercutlist`. If a panel
    showed up there more than once, the first sheet is kept. Panels missing from the view
    or from `pack_item` are still imported, with those fields left blank.
21. **Meta codes:** `project_code` / `client_code` / `order_no` that are empty or `NO_PROJECT`
    are ignored. Otherwise a mismatch is stored in `f4p_warnings` and shown as an orange
    banner; it never blocks the import. `order_no` counts as matching if it equals the order
    name, the `NN` suffix, `ORD-NN`, or the same number without leading zeros.
22. **Import is blocked on Cancelled orders**, allowed on every other status.
23. **Order Panel** is `in_create` + `read_only`: rows only come from the import.
24. `sealed_at` `2026-09-11T23:50:02` is stored as a Datetime `2026-09-11 23:50:02`.

## Phase 3 — Inventory

25. **Location links use `production_order`**, not `order` (same reason as item 14).
26. **Stock Location** is named `LOC-0001` with an auto-built title ("General Store",
    "Project: P0001 - Kitchen", ...). At most one location per scope + link. Picking an order
    fills its project and client, and picking a project fills its client, so a client filter
    also finds project and order stock. The General Store is created by `after_install` and
    `after_migrate`, which also covers sites set up in Phases 1–2.
27. **Stock Movement fields:** `location` is where the stock is (or "into" for Receipt,
    "from" for Transfer). `target_location` is used only for Transfer, and `from_state`
    (Received / In Process, default In Process) only for Dispatch.
28. **"Both are projects" rule** = the two locations belong to *different projects*. That
    covers Project and Order locations alike, and doesn't count moving project stock into
    that project's own order, or stock from the General / client store. Approver = the user
    who submits.
29. **Transfers only move Received stock.** In Process stock has to be returned first.
30. **Balance check** nets all rows of one movement per (location, state, item) and compares
    with the current ledger sum. Cancel runs the same check on the reversing rows, so a
    receipt can't be cancelled once its stock has been issued. Back-dated movements are
    checked against today's balance, not the balance on their date.
31. **Concurrency:** the movement's locations are row-locked (`SELECT ... FOR UPDATE`) before
    the balance check, so two submits on the same stock can't both pass.
32. **Ledger rows** also store client / project / production_order copied from the location,
    which keeps report filters simple. Rows can't be edited or deleted (controller guards +
    read-only permissions). Cancel adds rows flagged `is_cancellation`.
33. **Stock Item** is named by `item_code`. The "core sheet" kind is shown as "Core Sheet".
    The default rate fills empty item rates on movements.
34. **Order Material Line `stock_item`** was added now (see item 15). Mapping is manual. The
    Order Material Status report sums `order_qty` per stock item and counts only stock at that
    order's own location(s). Shortfall = required − (received + in process + sent), floored at 0.
    Unmapped lines show their full requirement as shortfall.
35. **Reports** live in `inventory/report/`, because Frappe requires reports inside a module.
    Stock Balance has an "As On" date. Stock Ledger shows a running balance that starts from
    the balance before From Date.
36. Quantities are rounded to 6 decimals in all checks, so 0.1 + 0.2 covers 0.3.

## Phase 4 — Billing

37. **Company state comes from a new single doctype, Cabinet Settings** (company name,
    GSTIN, state, default GST rate 18%, default due days 15). The spec didn't say where the
    seller's state lives, and GST needs it.
38. **Place of supply** defaults to the client's state, else the company state. Same state →
    CGST + SGST, else IGST. An empty place of supply counts as the same state.
39. **GST is computed per rate group** (sum of line amounts × rate), rounded to paise. CGST and
    SGST are each half-rate and rounded separately, so they're always equal. Amounts use
    Decimal. `rounded_total` = nearest rupee, with .50 rounding up.
40. **Only Tax Invoices are receivables.** Quotation, Proforma and Credit Note have outstanding
    0 and an extra status, **Issued**, which isn't in the spec list. Payments are only allowed
    against submitted Tax Invoices, and never above the outstanding (no overpayment / advances in v1).
41. **Credit Note** needs `Against Invoice` (a submitted Tax Invoice for the same client). It
    can't exceed that invoice's outstanding. On submit or cancel it updates the invoice's
    `credited_amount`. Outstanding = rounded_total − paid − credited.
42. **Status:** Overdue wins over Unpaid / Partly Paid once the due date has passed (due today
    is not overdue). Paid wins over everything. Paid / credited / outstanding / status are
    always recomputed from the submitted payments and credit notes, not added up, so cancels
    can't drift them.
43. **Concurrency:** the invoice row is locked (`FOR UPDATE`) before a payment or credit note is
    checked against its outstanding.
44. **Cancel rules** come from Frappe's link checks: an invoice with submitted payments or credit
    notes can't be cancelled until they are.
45. **Due date** only applies to Tax Invoices. It defaults to posting date + default due days
    and can't be before the posting date.
46. **Project / order filters:** choosing an order fills its project. The project must belong
    to the client and the order to the project.
47. **Make from Order:** "lines" gives one row per material line (qty = order_qty, rate =
    unit_price, UOM Sheet / m / kg). "lump_sum" gives one row at `cost_grand`. Both use the
    default GST rate. HSN/SAC is left blank to fill in.
48. **Payment reference_no** is required for every mode except Cash.
49. **Reports:** the Invoice Register shows Credit Notes as negative so the totals row nets them,
    and hides cancelled invoices unless Status = Cancelled. Receivables Ageing counts days from the due
    date (posting date if none). Not-yet-due goes in 0–30, and it uses the current outstanding.
    Project Billing Summary: invoiced = Tax Invoices − Credit Notes; margin = invoiced excl.
    GST − sum of non-cancelled orders' `cost_grand`.
50. **Daily scheduler** (`billing.tasks.mark_overdue`) re-checks submitted, unpaid Tax Invoices
    that are past due.

## Process

51. From Phase 4 on, the owner asked to merge straight to `main` instead of leaving PRs open.
    PR #1 (Phases 1–4) was merged by Claude.

## Demo and live preview

52. **Two previews**, because GitHub can't host a running Frappe server:
    - **Demo site (GitHub Pages):** static HTML + JS reading `data.json`. CI builds that file by
      running the dummy dataset through the app's pure-Python logic (`parse_f4p`, stock rules,
      GST / status rules), so the demo can't drift from the code. It's read-only.
    - **Live preview (Codespaces):** `.devcontainer/` runs `frappe/bench` + MariaDB 10.6 +
      Redis, initialises a Frappe `version-15` bench, gets CRM (`main` branch, which can be
      changed with `CRM_BRANCH`), symlinks this repo as `apps/cabinet_erp`, creates
      `cabinet.localhost`, and loads the demo data. The admin password is `admin`, which is
      fine for a throwaway personal codespace and must never be reused anywhere real.
53. **One dummy dataset** (`cabinet_erp/demo_data.py`), used by both previews. The names and
    GSTINs are made up (the GSTINs are format- and checksum-valid). The sample seal has no
    prices, so demo prices per stock item are applied to its material lines and order costs.
    `tests/test_demo_data.py` keeps the dataset valid.
54. **CI:** `tests.yml` runs pytest, json.tool and the demo build on every push and PR.
    `pages.yml` deploys the site from `main`. GitHub Pages has to be switched to
    "GitHub Actions" once in the repo settings.

## Phase 5 — CRM glue, roles, workspace, PDFs

55. **Roles** (Cabinet Admin, Sales, Production, Accounts) are created in code
    (`before_install` / `before_migrate`, so they exist before doctype permissions sync),
    not as fixtures. System Manager keeps full access everywhere.
56. **Permission matrix** (spec §5):
    - Sales: clients and projects get create/edit, invoices get create/edit but not submit,
      orders and payments are read-only.
    - Production: orders, stock items, locations and movements, including submit/cancel.
    - Accounts: invoices and payments including submit/cancel, plus Cabinet Settings.
    - Everyone else gets read where they need it for links.
    - Stock Ledger Entry is read-only for every role.
    - Reports follow their module.
57. **CRM permissions are not changed.** Adding Custom DocPerms to CRM doctypes would replace
    CRM's own standard permissions. Sales users should also get CRM's built-in "Sales User" role.
58. **Deal Won → client:** `doc_events` on CRM Deal `on_update`, which fires only on the
    transition to Won (not on later saves).
    - If the deal's organization is already a client, it is linked silently.
    - Otherwise the user gets a dialog with a "Create Cabinet Client" server action, and the deal
      owner gets a ToDo, because the CRM's Vue UI doesn't run Desk form scripts.
    - The link is stored on a custom field `CRM Deal.cabinet_client`, created in `after_migrate`,
      and on `Cabinet Client.crm_deal`.
    - Client type: B2B if the deal has an organization, else B2C. The primary contact comes from
      the deal's contacts table.
59. **Workspace "Cabinet ERP"** (module Clients): 8 shortcuts and 7 link cards, CRM included.
60. **PDFs:** four standard Jinja Print Formats. Each one is a one-line `include` of a template
    in `templates/print/`, with data from `cabinet_print(doc)` (a registered Jinja method).
    The templates only use that dict plus three `cab_*` filters, so the static demo renders
    the very same files with plain Jinja2 and makes real PDFs with headless Chromium in CI.
    The layout is table-based because Frappe's default PDF engine (wkhtmltopdf) has weak CSS
    support. Each print format is the default for its doctype, and the forms get a
    **Download PDF** button that uses Frappe's own `download_pdf` endpoint.
61. **Amount in words** uses the Indian system (lakh / crore) and is written in Python, not
    Frappe's `money_in_words`, so the demo build doesn't need Frappe. The GST summary per rate
    is rounded exactly like the invoice totals, and a test checks they match.
