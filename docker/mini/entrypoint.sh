#!/usr/bin/env bash
# Start Postgres, create the instance on first start, then run web + worker.
set -euo pipefail
PG=/usr/lib/postgresql/17/bin
first=
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  "$PG/initdb" -D "$PGDATA" -U zenodo --auth=trust >/dev/null
  printf "shared_preload_libraries = 'pg_search'\nshared_buffers = 64MB\n" >> "$PGDATA/postgresql.conf"
  first=1
fi
"$PG/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" -w start
[ -n "$first" ] && "$PG/createdb" -U zenodo zenodo
# invenio.cfg reads it from ZENODO_SECRET_KEY_FILE, also for `docker exec invenio ...`
[ -s "$ZENODO_SECRET_KEY_FILE" ] || head -c 32 /dev/urandom | base64 > "$ZENODO_SECRET_KEY_FILE"
# HTTPS with a self-signed certificate, kept in the volume like the data
TLS_CERT="$PGDATA/tls.crt" TLS_KEY="$PGDATA/tls.key"
[ -s "$TLS_CERT" ] || openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  -keyout "$TLS_KEY" -out "$TLS_CERT" 2>/dev/null
export TLS_CERT TLS_KEY
trap '"$PG/pg_ctl" -D "$PGDATA" -m fast stop' EXIT
cd /opt/invenio/src
[ -n "$first" ] && ./wipe_recreate.sh
# Every process holds its own copy of the app (~150-300 MiB), so run two: the
# worker, which runs tasks itself (solo pool) and beat in a thread
# (ZENODO_BEAT=thread), and Werkzeug's threaded server, which serves HTTPS
# from one process (uwsgi's master + worker hold two copies of the app).
# To scale up: WORKER_POOL=prefork WORKER_CONCURRENCY=n, ZENODO_BEAT=process
# (celery -B), and WEB_SERVER=uwsgi WEB_PROCESSES=n.
export ZENODO_BEAT="${ZENODO_BEAT:-thread}"
celery -A invenio_app.celery worker --loglevel=INFO \
  $([ "$ZENODO_BEAT" = process ] && echo -B) \
  --pool="${WORKER_POOL:-solo}" --concurrency="${WORKER_CONCURRENCY:-1}" \
  --queues=celery,low,indexing --schedule="$PGDATA/celerybeat-schedule" &
if [ "${WEB_SERVER:-werkzeug}" = uwsgi ]; then
  uwsgi --https "0.0.0.0:5000,$TLS_CERT,$TLS_KEY" --module invenio_app.wsgi:application \
    --master --processes "${WEB_PROCESSES:-2}" --threads 4 --die-on-term &
else
  python -c 'import os
from werkzeug.serving import run_simple
from invenio_app.wsgi import application
run_simple("0.0.0.0", 5000, application, threaded=True,
           ssl_context=(os.environ["TLS_CERT"], os.environ["TLS_KEY"]))' &
fi
wait -n
