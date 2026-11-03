#!/usr/bin/env bash
# One-time setup for the live preview: bench + Frappe CRM + this app + demo data.
# Safe to re-run; every step skips work that is already done.
set -euo pipefail

FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-15}"
CRM_BRANCH="${CRM_BRANCH:-main}"
SITE="cabinet.localhost"
BENCH="$HOME/frappe-bench"

git config --global --add safe.directory /workspace

if [ ! -d "$BENCH" ]; then
  echo ">>> bench init (Frappe $FRAPPE_BRANCH) - this is the slow part"
  bench init --skip-redis-config-generation --frappe-branch "$FRAPPE_BRANCH" "$BENCH"
fi
cd "$BENCH"

bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
# Redis runs in its own containers, so don't start it from the Procfile.
sed -i '/^redis/d' Procfile

echo ">>> waiting for MariaDB"
for _ in $(seq 1 60); do
  python3 -c "import socket; socket.create_connection(('mariadb', 3306), 2)" 2>/dev/null && break
  sleep 2
done

if [ ! -d apps/crm ]; then
  echo ">>> get-app crm ($CRM_BRANCH)"
  bench get-app crm --branch "$CRM_BRANCH"
fi

if [ ! -e apps/cabinet_erp ]; then
  echo ">>> linking this repo as apps/cabinet_erp (edits in /workspace are live)"
  ln -s /workspace apps/cabinet_erp
  ./env/bin/pip install -q -e apps/cabinet_erp
fi
# apps.txt may not end with a newline; appending blindly would glue names together
# ("crmcabinet_erp"), so rewrite it as one clean name per line.
# (Also repairs a file already broken that way by an earlier version of this script.)
{ cat sites/apps.txt; echo; echo cabinet_erp; } \
  | sed 's/^crmcabinet_erp$/crm/' | tr -s '[:space:]' '\n' | sed '/^$/d' | awk '!seen[$0]++' > sites/apps.txt.new
mv sites/apps.txt.new sites/apps.txt

if [ ! -d "sites/$SITE" ]; then
  echo ">>> new-site $SITE"
  bench new-site "$SITE" \
    --db-root-password 123 \
    --admin-password admin \
    --mariadb-user-host-login-scope='%' \
    --install-app crm \
    --install-app cabinet_erp
  bench --site "$SITE" execute cabinet_erp.demo.setup_demo
fi

bench use "$SITE"
bench --site "$SITE" enable-scheduler
bench build --app cabinet_erp || true

echo ">>> setup done. Login: Administrator / admin"
