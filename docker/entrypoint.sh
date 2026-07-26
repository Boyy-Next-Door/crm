#!/usr/bin/env bash
# ------------------------------------------------------------
# Runtime entrypoint for the CRM container.
#
# The image is baked with apps installed, but sites/ is a mounted volume so
# that the DB config, uploaded files, and encryption key persist. On first
# boot we restore the seed sites/ dir and create the crm.localhost site;
# on every subsequent boot we just wait for services and run bench start.
# ------------------------------------------------------------
set -euo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
SITE="${SITE_NAME:-crm.localhost}"
DB_HOST="${DB_HOST:-mariadb}"
DB_ROOT_PWD="${DB_ROOT_PASSWORD:-123}"
ADMIN_PWD="${ADMIN_PASSWORD:-admin}"
REDIS_URL_CACHE="${REDIS_CACHE:-redis://redis:6379}"
REDIS_URL_QUEUE="${REDIS_QUEUE:-redis://redis:6379}"
REDIS_URL_SOCKETIO="${REDIS_SOCKETIO:-redis://redis:6379}"

# Site behaviour toggles — override from docker-compose environment.
# Set MUTE_EMAILS=0 in production so outgoing mail actually goes out.
# DEVELOPER_MODE=0 in production too (turns off auto-reload, hides debug info).
MUTE_EMAILS="${MUTE_EMAILS:-1}"
DEVELOPER_MODE="${DEVELOPER_MODE:-1}"
SERVER_SCRIPT_ENABLED="${SERVER_SCRIPT_ENABLED:-1}"
SITE_LANG="${SITE_LANG:-zh}"

cd "$BENCH_DIR"

# Restore a fresh sites/ tree if the volume is empty (first boot).
if [ ! -f "$BENCH_DIR/sites/common_site_config.json" ]; then
  echo "[entrypoint] Empty sites volume detected, seeding from image..."
  cp -a /home/frappe/sites-seed/. "$BENCH_DIR/sites/"
fi

# Refresh built asset bundles (sites/assets/) from the image on every boot.
# We persist all of sites/ in a named volume, so a freshly baked image would
# otherwise be masked by the old assets in that volume — the user would have
# to run `bench build` manually to see any frontend change. Restoring assets
# here means `docker compose build && up` alone is enough.
if [ -d /home/frappe/sites-seed/assets ]; then
  echo "[entrypoint] Refreshing sites/assets/ from image..."
  rm -rf "$BENCH_DIR/sites/assets"
  cp -a /home/frappe/sites-seed/assets "$BENCH_DIR/sites/assets"
fi

# Wire hostnames every boot — cheap and idempotent, handles compose network changes.
bench set-mariadb-host "$DB_HOST"                       >/dev/null
bench set-redis-cache-host "$REDIS_URL_CACHE"           >/dev/null
bench set-redis-queue-host "$REDIS_URL_QUEUE"           >/dev/null
bench set-redis-socketio-host "$REDIS_URL_SOCKETIO"     >/dev/null

# Wait for MariaDB to accept connections before we try to create a site.
echo "[entrypoint] Waiting for MariaDB at ${DB_HOST}:3306 ..."
for i in $(seq 1 60); do
  if (echo > /dev/tcp/${DB_HOST}/3306) >/dev/null 2>&1; then
    echo "[entrypoint] MariaDB is up."
    break
  fi
  sleep 2
done

# Create the site on first boot only.
if [ ! -d "$BENCH_DIR/sites/$SITE" ]; then
  echo "[entrypoint] Creating site $SITE ..."
  bench new-site "$SITE" \
      --mariadb-root-password "$DB_ROOT_PWD" \
      --admin-password "$ADMIN_PWD" \
      --no-mariadb-socket \
      --install-app crm

  bench --site "$SITE" set-config developer_mode "$DEVELOPER_MODE"
  bench --site "$SITE" set-config mute_emails "$MUTE_EMAILS"
  bench --site "$SITE" set-config server_script_enabled "$SERVER_SCRIPT_ENABLED"

  # Force Simplified Chinese as the site default; the install hook also
  # writes System Settings.language but this covers the site-config layer
  # (which Frappe reads before a user is logged in).
  bench --site "$SITE" set-config lang "$SITE_LANG"

  bench use "$SITE"
  bench --site "$SITE" clear-cache
  echo "[entrypoint] Site $SITE ready — Administrator / $ADMIN_PWD"
  echo "[entrypoint] mute_emails=$MUTE_EMAILS, developer_mode=$DEVELOPER_MODE"
else
  echo "[entrypoint] Site $SITE already provisioned, skipping bootstrap."
  bench use "$SITE"
  # Re-apply site behaviour config on every boot so environment overrides
  # (MUTE_EMAILS, DEVELOPER_MODE …) take effect for existing sites without
  # a manual `bench set-config`. Comment these out if you want the values
  # set on first boot to be sticky.
  bench --site "$SITE" set-config developer_mode "$DEVELOPER_MODE" >/dev/null
  bench --site "$SITE" set-config mute_emails "$MUTE_EMAILS" >/dev/null
  bench --site "$SITE" set-config server_script_enabled "$SERVER_SCRIPT_ENABLED" >/dev/null
  echo "[entrypoint] Config refreshed: mute_emails=$MUTE_EMAILS, developer_mode=$DEVELOPER_MODE"
  # Run any new patches shipped in the image (DocType structure, custom
  # fields, data backfills). No-op if there's nothing new. Failure here
  # shouldn't wedge the boot, so we swallow it and just log.
  echo "[entrypoint] Running pending migrations..."
  bench --site "$SITE" migrate 2>&1 | tail -20 || echo "[entrypoint] migrate returned non-zero (continuing)"
  # Clear translation & meta cache so any new zh.po lines or DocType changes
  # baked into the image take effect without a manual `bench clear-cache`.
  bench --site "$SITE" clear-cache >/dev/null 2>&1 || true
fi

# Strip redis/watch lines from Procfile if this bench happens to have them —
# our stack runs redis in its own container.
sed -i '/redis/d;/watch/d' "$BENCH_DIR/Procfile" 2>/dev/null || true

exec "$@"
