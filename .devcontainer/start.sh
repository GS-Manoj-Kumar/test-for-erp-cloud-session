#!/usr/bin/env bash
# Start the dev server in the background each time the codespace starts. Logs: ~/bench.log
cd "$HOME/frappe-bench" || { echo "bench not set up yet; run: bash .devcontainer/setup.sh"; exit 0; }
# Bridge so Codespaces forwarding reaches the IPv4-only dev server (fixes HTTP 502). Logs: ~/bridge.log
pgrep -f ipv6_bridge.py >/dev/null || setsid nohup python3 /workspace/.devcontainer/ipv6_bridge.py 8000 9000 8080:8000 > "$HOME/bridge.log" 2>&1 < /dev/null &
pgrep -f "frappe.utils.bench_helper frappe serve" >/dev/null && exit 0
setsid nohup bench start > "$HOME/bench.log" 2>&1 < /dev/null &
echo "bench start launched; open the forwarded port 8080 (login Administrator / admin)"
