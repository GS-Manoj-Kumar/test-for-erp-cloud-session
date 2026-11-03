// Cabinet ERP static demo. Read-only views over data.json (built by scripts/build_demo_site.py).
(function () {
  "use strict";

  const REPO = "GS-Manoj-Kumar/test-for-erp-cloud-session";
  const CODESPACE_URL = `https://codespaces.new/${REPO}?quickstart=1`;

  // Which field links to which doctype.
  const LINKS = {
    client: "Cabinet Client", project: "Cabinet Project", production_order: "Production Order",
    location: "Stock Location", target_location: "Stock Location", stock_item: "Stock Item",
    movement: "Stock Movement", invoice: "Cabinet Invoice", return_against: "Cabinet Invoice",
  };
  const MONEY = new Set(["rate", "amount", "unit_price", "line_total", "net_total", "cgst", "sgst", "igst",
    "total_tax", "grand_total", "rounding_adjustment", "rounded_total", "paid_amount", "credited_amount",
    "outstanding_amount", "invoice_outstanding", "default_rate", "total_amount", "cost_core", "cost_laminate",
    "cost_glue", "cost_edge_band", "cost_grand", "invoiced", "invoiced_net", "paid", "outstanding",
    "order_cost", "margin", "b_0_30", "b_31_60", "b_61_90", "b_90_plus"]);
  const NUMBER = new Set(["qty", "order_qty", "wastage_pct", "qty_change", "balance", "received", "in_process",
    "sent", "total", "required", "shortfall", "panel_count", "variety_count", "sheet_count", "thickness",
    "finished_length", "finished_width", "area", "quantity", "panel_index", "sheet_index", "board_index",
    "total_qty", "days_overdue", "margin_pct"]);
  const DATE = new Set(["posting_date", "due_date", "token_booking", "advance_paid", "confirmation",
    "target_handover", "estimated_handover", "actual_handover"]);
  const STATUS_COLOR = {
    Paid: "green", Delivered: "green", Handover: "green", Closed: "green", Submitted: "blue",
    "Partly Paid": "orange", Unpaid: "orange", Cutting: "orange", "Edge Banding": "orange", Production: "orange",
    Overdue: "red", Cancelled: "red", Issued: "blue", Dispatched: "blue", Packed: "blue", Released: "blue",
    Draft: "gray", Enquiry: "gray", Design: "blue", Confirmed: "blue",
    Received: "green", "In Process": "orange", Sent: "blue",
  };
  const LABEL = {
    name: "ID", client_name: "Client Name", client_type: "Type", project_name: "Project", order_title: "Order Title",
    production_order: "Order", stock_item: "Stock Item", item_name: "Item Name", uom: "UOM", gstin: "GSTIN",
    hsn_sac: "HSN/SAC", gst_rate: "GST %", cgst: "CGST", sgst: "SGST", igst: "IGST", qty_change: "Qty Change",
    b_0_30: "0-30", b_31_60: "31-60", b_61_90: "61-90", b_90_plus: "90+", nas_path: "NAS Path",
    skp_name: "SketchUp File", f4p_file: "F4P File", seal_id: "Seal ID", is_inter_state: "Inter-State (IGST)",
    margin_pct: "Margin %", wastage_pct: "Wastage %", assigned_pm: "Assigned PM",
  };

  // List columns + form layout per doctype.
  const DOCTYPES = {
    "Cabinet Client": {
      module: "Clients", title: "client_name",
      list: ["name", "client_name", "client_type", "phone", "state", "gstin"],
      form: [["Client", ["client_name", "client_type", "phone", "email"]],
             ["Tax", ["gstin", "state"]], ["Address", ["billing_address", "shipping_address"]]],
      related: [["Cabinet Project", "client", "Projects"], ["Production Order", "client", "Production Orders"],
                ["Cabinet Invoice", "client", "Invoices"], ["Payment Entry Lite", "client", "Payments"]],
    },
    "Cabinet Project": {
      module: "Clients", title: "project_name",
      list: ["name", "project_name", "client", "client_name", "milestone", "project_type", "target_handover"],
      form: [["Project", ["project_name", "client", "client_name", "project_type", "property_type", "milestone"]],
             ["Dates", ["token_booking", "advance_paid", "confirmation", "target_handover", "estimated_handover", "actual_handover"]],
             ["NAS", ["nas_path"]]],
      status: "milestone",
      related: [["Production Order", "project", "Production Orders"], ["Cabinet Invoice", "project", "Invoices"],
                ["Stock Location", "project", "Stock Locations"]],
    },
    "Production Order": {
      module: "Production", title: "order_title",
      list: ["name", "order_title", "project", "client_name", "status", "panel_count", "cost_grand"],
      form: [["Order", ["order_title", "project", "project_name", "client", "client_name", "status"]],
             ["F4P Seal", ["seal_id", "sealed_at", "sealer_version", "skp_name", "f4p_file", "panel_count", "variety_count", "sheet_count"]],
             ["Costs (demo prices)", ["cost_core", "cost_laminate", "cost_glue", "cost_edge_band", "cost_grand"]]],
      tables: [["material_lines", "Material Requirements", ["kind", "description", "size", "qty", "order_qty", "wastage_pct", "unit_price", "line_total", "stock_item"]]],
      related: [["Order Panel", "production_order", "Panels"], ["Cabinet Invoice", "production_order", "Invoices"],
                ["Stock Location", "production_order", "Stock Locations"]],
      reportLink: "Order Material Status",
    },
    "Order Panel": {
      module: "Production", title: "panel_id",
      list: ["panel_id", "production_order", "material_name", "thickness", "finished_length", "finished_width", "quantity", "pack_group", "sheet_index"],
      form: [["Panel", ["production_order", "panel_id", "panel_index", "quantity", "code_name_1", "code_name_2", "code_name_3"]],
             ["Material", ["material_name", "thickness", "shape_type", "grain"]],
             ["Size and Placement", ["finished_length", "finished_width", "area", "sheet_index", "board_index", "pack_group"]],
             ["Edge Band and Status", ["edge_band_summary", "exclusion_status", "warnings"]]],
    },
    "Stock Item": {
      module: "Inventory", title: "item_name",
      list: ["name", "item_name", "kind", "uom", "thickness", "size_label", "default_rate"],
      form: [["Item", ["item_code", "item_name", "kind", "uom", "thickness", "size_label", "color", "default_rate"]]],
      related: [["Stock Ledger Entry", "stock_item", "Ledger"]],
    },
    "Stock Location": {
      module: "Inventory", title: "title",
      list: ["name", "title", "scope", "client", "project", "production_order"],
      form: [["Location", ["title", "scope", "client", "project", "production_order"]]],
      related: [["Stock Ledger Entry", "location", "Ledger"]],
    },
    "Stock Movement": {
      module: "Inventory", title: "movement_type",
      list: ["name", "movement_type", "posting_date", "location", "target_location", "total_qty", "status"],
      form: [["Movement", ["movement_type", "posting_date", "location", "target_location", "from_state", "status"]],
             ["Project-to-Project Transfer", ["is_urgent", "reason", "approver"]],
             ["Totals", ["total_qty", "total_amount", "remarks"]]],
      tables: [["items", "Items", ["stock_item", "item_name", "uom", "qty", "rate", "amount"]]],
      related: [["Stock Ledger Entry", "movement", "Ledger rows written on submit"]],
    },
    "Stock Ledger Entry": {
      module: "Inventory", title: "name",
      list: ["name", "posting_date", "movement", "location", "stock_item", "state", "qty_change"],
      form: [["Entry", ["posting_date", "stock_item", "location", "state", "qty_change", "rate"]],
             ["Voucher", ["voucher_type", "movement", "movement_type", "is_cancellation"]],
             ["Scope", ["client", "project", "production_order"]]],
      status: "state",
    },
    "Cabinet Invoice": {
      module: "Billing", title: "client_name",
      list: ["name", "invoice_type", "posting_date", "client_name", "project", "status", "rounded_total", "outstanding_amount"],
      form: [["Invoice", ["invoice_type", "client", "client_name", "project", "production_order", "return_against", "posting_date", "due_date", "status"]],
             ["GST", ["place_of_supply", "company_state", "is_inter_state"]],
             ["Totals", ["net_total", "cgst", "sgst", "igst", "total_tax", "grand_total", "rounding_adjustment", "rounded_total"]],
             ["Payment", ["paid_amount", "credited_amount", "outstanding_amount"]]],
      tables: [["items", "Items", ["description", "hsn_sac", "qty", "uom", "rate", "amount", "gst_rate"]]],
      related: [["Payment Entry Lite", "invoice", "Payments"], ["Cabinet Invoice", "return_against", "Credit Notes"]],
    },
    "Payment Entry Lite": {
      module: "Billing", title: "client_name",
      list: ["name", "posting_date", "client_name", "invoice", "mode", "amount", "status"],
      form: [["Payment", ["client", "client_name", "invoice", "posting_date", "amount", "mode", "reference_no", "status"]]],
    },
  };

  const REPORTS = {
    "Stock Balance": { module: "Inventory", cols: ["location", "location_title", "stock_item", "item_name", "uom", "received", "in_process", "sent", "total"],
      note: "Balance per location and item, split by state. Built from the Stock Ledger." },
    "Stock Ledger": { module: "Inventory", cols: ["posting_date", "movement", "movement_type", "location", "location_title", "stock_item", "state", "qty_change", "balance"],
      note: "Every ledger row in order, with a running balance per location / state / item." },
    "Order Material Status": { module: "Inventory", perOrder: true, cols: ["stock_item", "description", "kind", "required", "received", "in_process", "sent", "shortfall"],
      note: "What the order needs (Order Material Lines) vs what is booked to the order's stock location." },
    "Invoice Register": { module: "Billing", total: true, cols: ["name", "posting_date", "invoice_type", "status", "client_name", "project", "net_total", "cgst", "sgst", "igst", "rounded_total", "paid_amount", "outstanding_amount"],
      note: "Credit Notes are shown negative so the totals row nets them out." },
    "Receivables Ageing": { module: "Billing", total: true, cols: ["name", "client_name", "project", "posting_date", "due_date", "days_overdue", "outstanding_amount", "b_0_30", "b_31_60", "b_61_90", "b_90_plus"],
      note: "Unpaid Tax Invoices, aged by days past the due date." },
    "Project Billing Summary": { module: "Billing", total: true, cols: ["project", "project_name", "client", "invoiced", "invoiced_net", "paid", "outstanding", "order_cost", "margin", "margin_pct"],
      note: "Invoiced (Tax Invoices minus Credit Notes), paid, outstanding, and margin against order material cost." },
  };
  const MODULES = ["Clients", "Production", "Inventory", "Billing"];

  let DATA = null;
  const $main = document.getElementById("main");

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const slug = (s) => encodeURIComponent(s);
  const label = (f) => LABEL[f] || f.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
  const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 });
  const docs = (dt) => DATA.docs[dt] || [];
  const find = (dt, name) => docs(dt).find((d) => d.name === name);

  function fmtDate(v) {
    if (!v) return "";
    const d = new Date(String(v).slice(0, 10) + "T00:00:00");
    if (isNaN(d)) return esc(v);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  function cell(field, value, row) {
    if (value === null || value === undefined || value === "") return "";
    if (LINKS[field] && find(LINKS[field], value)) return `<a href="#/form/${slug(LINKS[field])}/${slug(value)}">${esc(value)}</a>`;
    if (field === "name" && row && row.__dt) return `<a href="#/form/${slug(row.__dt)}/${slug(value)}">${esc(value)}</a>`;
    if (["status", "milestone", "state"].includes(field)) return `<span class="pill ${STATUS_COLOR[value] || "gray"}">${esc(value)}</span>`;
    if (MONEY.has(field)) { const n = Number(value); return `<span class="${n < 0 ? "neg" : ""}">${inr.format(n)}</span>`; }
    if (field === "shortfall" && Number(value) > 0) return `<span class="neg">${num.format(value)}</span>`;
    if (NUMBER.has(field)) return num.format(Number(value));
    if (DATE.has(field)) return fmtDate(value);
    if (field === "is_urgent" || field === "is_inter_state" || field === "is_cancellation") return value ? "Yes" : "No";
    if (field === "sealed_at") return esc(String(value).replace("T", " "));
    return esc(value);
  }
  const isNum = (f) => MONEY.has(f) || NUMBER.has(f);

  function table(rows, cols, opts = {}) {
    if (!rows.length) return `<p class="muted pad">No rows.</p>`;
    const head = cols.map((c) => `<th class="${isNum(c) ? "num" : ""}">${esc(label(c))}</th>`).join("");
    const body = rows.map((r) => {
      const href = opts.dt ? `#/form/${slug(opts.dt)}/${slug(r.name)}` : "";
      const tds = cols.map((c) => `<td class="${isNum(c) ? "num" : ""}${c === "description" || c === "reason" || c === "location_title" ? " wrap" : ""}">${cell(c, r[c], opts.dt ? { ...r, __dt: opts.dt } : r)}</td>`).join("");
      return `<tr${href ? ` class="clickable" data-href="${href}"` : ""}>${tds}</tr>`;
    }).join("");
    let foot = "";
    if (opts.total) {
      const tds = cols.map((c, i) => {
        if (i === 0) return `<td>Total</td>`;
        if (MONEY.has(c)) return `<td class="num">${cell(c, rows.reduce((s, r) => s + Number(r[c] || 0), 0))}</td>`;
        return "<td></td>";
      }).join("");
      foot = `<tfoot><tr class="total">${tds}</tr></tfoot>`;
    }
    return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody>${foot}</table></div>`;
  }

  function matches(row, q) {
    if (!q) return true;
    q = q.toLowerCase();
    return Object.values(row).some((v) => typeof v !== "object" && String(v ?? "").toLowerCase().includes(q));
  }

  // ---------- sidebar ----------
  function sidebar(active) {
    let html = `<a href="#/" class="${active === "home" ? "active" : ""}">Home</a>
      <a href="#/documents" class="${active === "documents" ? "active" : ""}">📄 Print &amp; PDF</a>`;
    for (const m of MODULES) {
      html += `<h4>${m}</h4>`;
      for (const [dt, cfg] of Object.entries(DOCTYPES)) {
        if (cfg.module === m) html += `<a href="#/list/${slug(dt)}" class="${active === dt ? "active" : ""}">${esc(dt)}</a>`;
      }
      for (const [r, cfg] of Object.entries(REPORTS)) {
        if (cfg.module === m) html += `<a href="#/report/${slug(r)}" class="${active === r ? "active" : ""}">📊 ${esc(r)}</a>`;
      }
    }
    document.getElementById("sidebar").innerHTML = html;
  }

  // ---------- views ----------
  function home() {
    sidebar("home");
    const inv = docs("Cabinet Invoice");
    const receivable = inv.filter((i) => i.invoice_type === "Tax Invoice").reduce((s, i) => s + i.outstanding_amount, 0);
    const overdue = inv.filter((i) => i.status === "Overdue");
    const shortfalls = Object.entries(DATA.reports["Order Material Status"])
      .flatMap(([o, rows]) => rows.filter((r) => r.shortfall > 0).map((r) => ({ ...r, production_order: o })));
    const tile = (lbl, value, href, hint = "") =>
      `<a class="tile" href="${href}"><div class="label">${esc(lbl)}</div><div class="value">${value}</div><div class="hint">${esc(hint)}</div></a>`;
    const c = DATA.meta.company;
    $main.innerHTML = `
      <div class="page-head"><h1>Cabinet ERP</h1><span class="sub">${esc(c.company_name)} · ${esc(c.company_state)} · as of ${fmtDate(DATA.meta.today)}</span></div>
      <div class="note">A <b>read-only demo with dummy data</b> of the Frappe app in this repo. Every total here was worked out by
        the app's own Python code (GST, stock balances, F4P import from the sample seal). To click around the real app,
        use <a href="${CODESPACE_URL}" target="_blank" rel="noopener">Open live app</a> (a GitHub Codespace; first start takes about 10 minutes).</div>
      <div class="tiles">
        ${tile("Clients", docs("Cabinet Client").length, "#/list/Cabinet%20Client")}
        ${tile("Projects", docs("Cabinet Project").length, "#/list/Cabinet%20Project")}
        ${tile("Production Orders", docs("Production Order").length, "#/list/Production%20Order", `${docs("Order Panel").length} panels imported`)}
        ${tile("Stock Movements", docs("Stock Movement").length, "#/list/Stock%20Movement", `${docs("Stock Ledger Entry").length} ledger rows`)}
        ${tile("Receivables", inr.format(receivable), "#/report/Receivables%20Ageing", `${overdue.length} overdue`)}
        ${tile("Material shortfalls", shortfalls.length, "#/report/Order%20Material%20Status")}
        ${tile("PDF documents", Object.keys(DATA.meta.prints || {}).length, "#/documents", "invoices, receipts, cutlists, challans")}
      </div>
      <div class="grid2">
        <div class="card"><h3>Overdue invoices</h3>${table(overdue, ["name", "client_name", "due_date", "outstanding_amount"], { dt: "Cabinet Invoice" })}</div>
        <div class="card"><h3>Shortfalls</h3>${table(shortfalls, ["production_order", "stock_item", "required", "shortfall"])}</div>
      </div>
      <div class="card"><h3>Projects</h3>${table(docs("Cabinet Project"), DOCTYPES["Cabinet Project"].list, { dt: "Cabinet Project" })}</div>
      <p class="muted">Built from commit ${esc(DATA.meta.commit || "local")}. Source: <a href="https://github.com/${REPO}">${REPO}</a>.</p>`;
  }

  function list(dt, q = "") {
    const cfg = DOCTYPES[dt];
    if (!cfg) return notFound();
    sidebar(dt);
    const rows = docs(dt).filter((r) => matches(r, q));
    $main.innerHTML = `
      <div class="crumbs">${esc(cfg.module)}</div>
      <div class="page-head"><h1>${esc(dt)}</h1></div>
      <div class="toolbar"><input id="listSearch" type="search" placeholder="Filter ${esc(dt)}…" value="${esc(q)}">
        <span class="count">${rows.length} of ${docs(dt).length}</span></div>
      ${table(rows, cfg.list, { dt })}`;
    const box = document.getElementById("listSearch");
    box.addEventListener("input", () => { const pos = box.selectionStart; list(dt, box.value); const b = document.getElementById("listSearch"); b.focus(); b.setSelectionRange(pos, pos); });
  }

  function form(dt, name) {
    const cfg = DOCTYPES[dt];
    const doc = cfg && find(dt, name);
    if (!doc) return notFound();
    sidebar(dt);
    const statusField = cfg.status || "status";
    const sections = cfg.form.map(([title, fields]) => `
      <div class="card"><h3>${esc(title)}</h3><div class="body fields">
        ${fields.map((f) => `<div class="field"><label>${esc(label(f))}</label><div class="val">${cell(f, doc[f], doc)}</div></div>`).join("")}
      </div></div>`).join("");
    const tables = (cfg.tables || []).map(([f, title, cols]) =>
      `<div class="card"><h3>${esc(title)} (${(doc[f] || []).length})</h3>${table(doc[f] || [], cols)}</div>`).join("");
    const related = (cfg.related || []).map(([rdt, field, title]) => {
      const rows = docs(rdt).filter((r) => r[field] === doc.name);
      if (!rows.length) return "";
      const shown = rows.slice(0, 25);
      const more = rows.length > shown.length ? `<p class="muted pad">Showing ${shown.length} of ${rows.length}. <a href="#/list/${slug(rdt)}?q=${slug(doc.name)}">See all</a></p>` : "";
      return `<div class="card"><h3>${esc(title)} (${rows.length})</h3>${table(shown, DOCTYPES[rdt].list, { dt: rdt })}${more}</div>`;
    }).join("");
    const printLinks = (DATA.meta.prints || {})[doc.name]
      ? `<a href="print/${slug(doc.name)}.html">🖨 Print view</a><a href="pdf/${slug(doc.name)}.pdf" download>⬇ PDF</a>` : "";
    const reportLink = cfg.reportLink && DATA.reports[cfg.reportLink][doc.name]
      ? `<a href="#/report/${slug(cfg.reportLink)}?order=${slug(doc.name)}">📊 ${esc(cfg.reportLink)}</a>` : "";
    const alert = dt === "Production Order" && doc.seal_id
      ? `<div class="note">Panels and material lines were imported from the sample seal <b>${esc(doc.seal_id)}</b> by <code>parse_f4p()</code>. The seal has no prices, so demo prices are applied.</div>` : "";
    $main.innerHTML = `
      <div class="crumbs"><a href="#/list/${slug(dt)}">${esc(dt)}</a></div>
      <div class="page-head"><h1>${esc(doc[cfg.title] || doc.name)}</h1><span class="sub">${esc(doc.name)}</span>
        ${doc[statusField] ? cell(statusField, doc[statusField]) : ""}<span class="links">${printLinks}${reportLink}</span></div>
      ${alert}${sections}${tables}${related}`;
  }

  function report(name, params) {
    const cfg = REPORTS[name];
    if (!cfg) return notFound();
    sidebar(name);
    let rows = DATA.reports[name];
    let picker = "";
    if (cfg.perOrder) {
      const orders = Object.keys(rows);
      const order = params.get("order") || orders[0];
      picker = `<select id="orderPick">${orders.map((o) => `<option ${o === order ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
      rows = rows[order] || [];
    }
    const q = params.get("q") || "";
    const filtered = rows.filter((r) => matches(r, q));
    $main.innerHTML = `
      <div class="crumbs">${esc(cfg.module)} · Script Report</div>
      <div class="page-head"><h1>${esc(name)}</h1></div>
      <p class="muted">${esc(cfg.note)}</p>
      <div class="toolbar">${picker}<input id="repSearch" type="search" placeholder="Filter rows…" value="${esc(q)}">
        <span class="count">${filtered.length} rows</span></div>
      ${table(filtered, cfg.cols, { total: cfg.total })}`;
    const pick = document.getElementById("orderPick");
    if (pick) pick.addEventListener("change", () => { location.hash = `#/report/${slug(name)}?order=${slug(pick.value)}`; });
    const box = document.getElementById("repSearch");
    box.addEventListener("change", () => {
      const p = new URLSearchParams(params); if (box.value) p.set("q", box.value); else p.delete("q");
      location.hash = `#/report/${slug(name)}?${p}`;
    });
  }

  function documents() {
    sidebar("documents");
    const prints = DATA.meta.prints || {};
    const rows = Object.entries(prints).map(([name, dt]) => {
      const d = find(dt, name) || {};
      return { name, dt, title: d[DOCTYPES[dt].title] || "", date: d.posting_date || "" };
    });
    const FORMAT = { "Cabinet Invoice": "Cabinet Tax Invoice", "Payment Entry Lite": "Payment Receipt",
      "Production Order": "Production Cutlist", "Stock Movement": "Delivery Challan" };
    $main.innerHTML = `
      <div class="page-head"><h1>Print &amp; PDF</h1></div>
      <div class="note">These are the app's four print formats (${Object.values(FORMAT).map(esc).join(", ")}),
        rendered from the same Jinja templates Frappe uses for <b>Print</b> and <b>Download PDF</b>, filled with the demo data.</div>
      <div class="table-wrap"><table><thead><tr><th>Document</th><th>Type</th><th>Print format</th><th>Title</th><th>Date</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td><a href="#/form/${slug(r.dt)}/${slug(r.name)}">${esc(r.name)}</a></td><td>${esc(r.dt)}</td>
        <td>${esc(FORMAT[r.dt])}</td><td>${esc(r.title)}</td><td>${fmtDate(r.date)}</td>
        <td><a href="print/${slug(r.name)}.html">🖨 View</a> &nbsp; <a href="pdf/${slug(r.name)}.pdf" download>⬇ PDF</a></td></tr>`).join("")}
      </tbody></table></div>`;
  }

  function search(q) {
    sidebar("");
    const hits = [];
    for (const dt of Object.keys(DOCTYPES)) {
      if (dt === "Stock Ledger Entry" || dt === "Order Panel") continue;
      for (const d of docs(dt)) if (matches(d, q)) hits.push({ dt, name: d.name, title: d[DOCTYPES[dt].title] || d.name });
    }
    $main.innerHTML = `<div class="page-head"><h1>Search: ${esc(q)}</h1><span class="sub">${hits.length} results</span></div>
      <div class="table-wrap"><table><thead><tr><th>Type</th><th>ID</th><th>Title</th></tr></thead><tbody>
      ${hits.map((h) => `<tr class="clickable" data-href="#/form/${slug(h.dt)}/${slug(h.name)}"><td>${esc(h.dt)}</td><td>${esc(h.name)}</td><td>${esc(h.title)}</td></tr>`).join("")}
      </tbody></table></div>`;
  }

  function notFound() {
    sidebar("");
    $main.innerHTML = `<p class="pad">Not found. <a href="#/">Go home</a></p>`;
  }

  // ---------- router ----------
  function route() {
    document.getElementById("sidebar").classList.remove("open");
    const [path, query] = location.hash.replace(/^#/, "").split("?");
    const params = new URLSearchParams(query || "");
    const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
    if (parts[0] === "list") list(parts[1], params.get("q") || "");
    else if (parts[0] === "form") form(parts[1], parts.slice(2).join("/"));
    else if (parts[0] === "report") report(parts[1], params);
    else if (parts[0] === "search") search(params.get("q") || "");
    else if (parts[0] === "documents") documents();
    else home();
    window.scrollTo(0, 0);
  }

  document.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-href]");
    if (tr && !e.target.closest("a")) location.hash = tr.dataset.href;
  });
  document.getElementById("menuBtn").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
  document.getElementById("globalSearch").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.value.trim()) location.hash = `#/search?q=${slug(e.target.value.trim())}`;
  });
  document.getElementById("liveLink").href = CODESPACE_URL;
  window.addEventListener("hashchange", route);

  fetch("data.json").then((r) => r.json()).then((d) => { DATA = d; route(); })
    .catch(() => { $main.innerHTML = `<p class="pad">Could not load data.json. Run <code>python scripts/build_demo_site.py</code> first.</p>`; });
})();
