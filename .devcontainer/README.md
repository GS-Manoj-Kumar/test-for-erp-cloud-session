# Cabinet ERP live preview

This codespace runs the real app: Frappe v15, Frappe CRM, and `cabinet_erp`, with demo data.

1. **First start only:** setup runs by itself (bench init, CRM, site, demo data). It takes
   about 10–15 minutes. Watch it in the "Creating codespace" log.
2. Open the **Ports** tab and click the globe next to port **8080** (it usually opens by itself).
   8080 is the app through a small bridge (`ipv6_bridge.py`, started by `start.sh`), because
   Codespaces can't reach Frappe's dev server on 8000 directly (HTTP 502). Ports 8000 and
   9000 are internal; 502 there is expected. Live updates (realtime) don't work through
   8080, so reload the page to see changes made elsewhere.
3. Log in as **Administrator** / **admin**.
4. Try `/app/cabinet-client`, `/app/production-order`, `/app/query-report/Stock Balance`,
   `/app/query-report/Receivables Ageing`.

Useful commands (in the terminal):

```bash
tail -f ~/bench.log                      # server log
bash .devcontainer/start.sh              # start the server again if it stopped
cd ~/frappe-bench && bench --site cabinet.localhost migrate          # after pulling new doctype changes
cd ~/frappe-bench && bench --site cabinet.localhost run-tests --app cabinet_erp
```

The repo is linked into the bench as `apps/cabinet_erp`, so code edits here are live
(Python changes reload the dev server; doctype JSON changes need `migrate`).

Stop the codespace when you are done; it uses your free Codespaces hours (a 4-core
machine uses 4 core-hours per hour).
