# One container with everything: Postgres 17 + pg_search, uwsgi (UI and API) and
# Celery worker + beat. For demos and PR previews only; build the app image first:
#
#   docker compose -f docker-compose.mini.yml build
#   docker build -f docker/mini/Dockerfile -t zenodo-mini-all .
#   docker run -p 5000:5000 -v zenodo-mini:/var/lib/postgresql zenodo-mini-all
#
# The first start creates the database and loads the demo fixtures.
ARG APP_IMAGE=zenodo
FROM ${APP_IMAGE}

ARG PG_SEARCH_VERSION=0.27.0
# Search in Postgres through pg_search (SEARCH_HOSTS=paradedb://).
ARG INVENIO_SEARCH_PARADEDB_REF=0d1bc27
USER root
RUN uv pip install \
    "invenio-search-paradedb @ https://github.com/slint/invenio-search/archive/${INVENIO_SEARCH_PARADEDB_REF}.tar.gz"
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && apt-get install -y --no-install-recommends postgresql-17 postgresql-17-pgvector && \
    curl -fsSL -o /tmp/pg_search.deb \
      "https://github.com/paradedb/paradedb/releases/download/v${PG_SEARCH_VERSION}/postgresql-17-pg-search_${PG_SEARCH_VERSION}-1PARADEDB-trixie_amd64.deb" && \
    apt-get install -y --no-install-recommends /tmp/pg_search.deb && \
    apt-get purge -y gnupg && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/pg_search.deb && \
    mkdir -p /var/lib/postgresql /run/postgresql && \
    chown -R invenio:0 /var/lib/postgresql /run/postgresql

COPY --chown=invenio:0 invenio.cfg /opt/invenio/var/instance/invenio.cfg
COPY --chown=invenio:0 wipe_recreate.sh /opt/invenio/src/wipe_recreate.sh
COPY --chmod=755 docker/mini/entrypoint.sh /usr/local/bin/zenodo-mini

ENV ZENODO_STACK=mini \
    INVENIO_SEARCH_HOSTS=paradedb:// \
    PGDATA=/var/lib/postgresql/data \
    INVENIO_SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://zenodo@localhost:5432/zenodo \
    INVENIO_SITE_UI_URL=http://127.0.0.1:5000 \
    INVENIO_SITE_API_URL=http://127.0.0.1:5000/api \
    INVENIO_SESSION_COOKIE_SECURE=False \
    INVENIO_APP_DEFAULT_SECURE_HEADERS="{'force_https': False, 'session_cookie_secure': False, 'content_security_policy': {}}"
USER invenio
VOLUME /var/lib/postgresql
EXPOSE 5000
ENTRYPOINT ["zenodo-mini"]
