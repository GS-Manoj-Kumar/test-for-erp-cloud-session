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
