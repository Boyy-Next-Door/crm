# syntax=docker/dockerfile:1
# ------------------------------------------------------------
# Frappe CRM — production-ish local image
#
# Everything expensive (bench init, app install, python/node deps, frontend
# build) happens at build time so `docker compose up` starts in seconds.
# Data lives in named volumes so `down` + `up` keeps it.
# ------------------------------------------------------------
FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe

# Silence git warnings and set dummy author.
RUN git config --global --add safe.directory '*' \
 && git config --global user.email "build@frappe-crm.local" \
 && git config --global user.name  "docker-build"

# Copy CRM source; .dockerignore filters out build artifacts.
COPY --chown=frappe:frappe crm /home/frappe/crm-src

# 1. bench init with Frappe v16 (CRM requires >= 16.0 per pyproject.toml)
# 2. Manually install CRM app:
#    - Copy into apps/ and git-init it so bench treats it as a real app
#    - pip install -e into the bench venv
#    - Register in sites/apps.txt
# 3. Install CRM's Python dependencies via bench setup requirements
# 4. Build assets for both apps (no site needed for asset compilation in v16)
# 5. Stash the fresh sites/ tree (with apps.txt + common config) for runtime
RUN set -ex \
 && bench init \
      --skip-redis-config-generation \
      --frappe-branch version-16 \
      frappe-bench \
 && cd frappe-bench \
 && cp -r /home/frappe/crm-src apps/crm \
 && cd apps/crm \
 && git init -q && git add -A && git commit -q -m "build snapshot" \
 && cd ../.. \
 && ./env/bin/pip install --quiet --no-cache-dir -e ./apps/crm \
 && echo "crm" >> sites/apps.txt \
 && bench setup requirements \
 && bench build --apps frappe,crm \
 && cp -r sites /home/frappe/sites-seed \
 && rm -rf /home/frappe/crm-src /home/frappe/.cache /home/frappe/.npm /tmp/*

# The MariaDB client that ships in frappe/bench:latest is now 11.8, and from
# 11.4 the client requires TLS by default. Our server is mariadb:10.8 with no
# certificates configured, so every CLI connection fails with
#   ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does
#   not support it
# That breaks `bench new-site` and, more importantly, `bench restore` -- both
# shell out to the `mariadb` / `mariadb-dump` binaries. The app itself is
# unaffected: MySQLdb (the Python driver) never asked for TLS.
#
# Opting the client out is safe here because MariaDB is only reachable on the
# private compose network and was never speaking TLS in the first place. The
# alternative -- issuing certs for a container-internal hop -- buys nothing.
RUN printf '[client]\nssl=0\n' > /home/frappe/.my.cnf

WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
RUN chmod +x /home/frappe/entrypoint.sh

EXPOSE 8000 9000

ENTRYPOINT ["/home/frappe/entrypoint.sh"]
CMD ["bench", "start"]
