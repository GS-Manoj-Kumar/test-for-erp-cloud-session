#!/usr/bin/env bash
# Start the dev server in the background each time the codespace starts. Logs: ~/bench.log
cd "$HOME/frappe-bench" || { echo "bench not set up yet; run: bash .devcontainer/setup.sh"; exit 0; }
pgrep -f "frappe.utils.bench_helper frappe serve" >/dev/null && exit 0
setsid nohup bench start > "$HOME/bench.log" 2>&1 < /dev/null &
echo "bench start launched; open the forwarded port 8000 (login Administrator / admin)"
