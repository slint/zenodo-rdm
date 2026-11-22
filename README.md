<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://about.zenodo.org/static/img/logos/zenodo-white-border.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://about.zenodo.org/static/img/logos/zenodo-black-border.svg">
    <img alt="Zenodo logo" src="https://about.zenodo.org/static/img/logos/zenodo-white-border.svg" width="500">
  </picture>
</div>

## Development quick start

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)
- [Docker](https://docs.docker.com/get-docker/)
- [Node.js 24.x](https://nodejs.org/) and [`pnpm` 12.x](https://pnpm.io/installation)
- [`libvips-dev`](https://www.libvips.org/install.html)

### Setup

Run the following commands:

```bash
git clone https://github.com/zenodo/zenodo-rdm.git
cd zenodo-rdm
uv tool install invenio-cli
invenio-cli check-requirements --development
invenio-cli install
invenio-cli services setup
invenio-cli run
```

### Mini stack

For demos, development and PR previews,
`ZENODO_STACK=mini` runs Zenodo without Redis or RabbitMQ:
Postgres (the ParadeDB image) holds the cache, locks, sessions, rate limits,
the Celery broker and results, and the indexing and stats queues
(on [PGMQ](https://github.com/pgmq/pgmq), installed as plain SQL by `wipe_recreate.sh`).
Search runs on a small OpenSearch container here;
the all-in-one image below searches in Postgres instead.
Production keeps the full stack.

```bash
docker compose -f docker-compose.mini.yml build
docker compose -f docker-compose.mini.yml run --rm app ./wipe_recreate.sh
docker compose -f docker-compose.mini.yml up -d  # http://127.0.0.1:5000
```

To develop against it with a local virtualenv,
install the `mini` extra (`uv sync --extra mini`),
start only `db` and `search` from `docker-compose.mini.yml`,
export `ZENODO_STACK=mini` and `INVENIO_SEARCH_HOSTS="['localhost:9200']"`,
and run the web app and the worker:

```bash
uwsgi --http :5000 --module invenio_app.wsgi:application --master --processes 2
celery -A invenio_app.celery worker --beat --loglevel=INFO
```

For a single container with Postgres, the web app and the worker inside,
searching through pg_search with
[invenio-search-paradedb](https://github.com/slint/invenio-search/tree/invenio-search-paradedb)
(`SEARCH_HOSTS=paradedb://`),
build on top of the app image:

```bash
docker compose -f docker-compose.mini.yml build app
docker build -f docker/mini/Dockerfile -t zenodo-mini-all .
docker run -p 5000:5000 -v zenodo-mini:/var/lib/postgresql zenodo-mini-all
```

The first start creates the database and loads the demo fixtures.
It keeps processes few (one uwsgi worker, and a solo Celery worker with beat)
and fits in 1.25 GB of memory, including an extra `invenio shell`;
set `WEB_PROCESSES`, `WORKER_POOL=prefork` and `WORKER_CONCURRENCY` to use more.

### Update dependencies

#### Python

1. Run `invenio-cli packages lock`
2. (Optional) Use [`changelog.py`](https://github.com/slint/changelog.py) to generate the commit message via `changelog-py --package-filter "^invenio" --show-major-bumps --since HEAD`
3. Commit the updated `uv.lock`

> [!TIP]
> To selectively update a specific package, you can use:
>
> ```bash
> uv lock --upgrade-package <package-name>
> ```

#### JavaScript

1. Run `invenio-cli assets lock`
2. Commit the updated `pnpm-lock.yaml` and `package.json`

## Tests

Tests can be run by activating the `uv` virtual env first:

```bash
cd zenodo-rdm
source .venv/bin/activate
(zenodo-rdm-app)$ ./run-tests.sh
```
