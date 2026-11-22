#!/usr/bin/env bash
# Start Postgres, create the instance on first start, then run web + worker.
set -euo pipefail
PG=/usr/lib/postgresql/17/bin
first=
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  "$PG/initdb" -D "$PGDATA" -U zenodo --auth=trust >/dev/null
  echo "shared_preload_libraries = 'pg_search'" >> "$PGDATA/postgresql.conf"
  first=1
fi
"$PG/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" -w start
[ -n "$first" ] && "$PG/createdb" -U zenodo zenodo
export INVENIO_SECRET_KEY="${INVENIO_SECRET_KEY:-$(cat "$PGDATA/secret_key" 2>/dev/null || head -c 32 /dev/urandom | base64 | tee "$PGDATA/secret_key")}"
trap '"$PG/pg_ctl" -D "$PGDATA" -m fast stop' EXIT
cd /opt/invenio/src
[ -n "$first" ] && ./wipe_recreate.sh
celery -A invenio_app.celery worker --beat --loglevel=INFO --concurrency=2 \
  --queues=celery,low,indexing --schedule="$PGDATA/celerybeat-schedule" &
uwsgi --http 0.0.0.0:5000 --module invenio_app.wsgi:application \
  --master --processes 2 --threads 2 --die-on-term &
wait -n
