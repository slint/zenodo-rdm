# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Celery broker and invenio-queues on PGMQ, in the same Postgres.

PGMQ deletes a message when it's acknowledged, so the queue tables stay small
without a cleanup job. It is installed from SQL (``install``), so Postgres needs
no extension files.
"""

import atexit
import hashlib
import os
import threading

from celery.beat import EmbeddedService
from celery.signals import celeryd_after_setup, worker_init, worker_shutdown
from kombu.transport import TRANSPORT_ALIASES, pgmq
from psycopg import connect, sql
from sqlalchemy.engine import make_url

OPTIONS = {
    # Installed from SQL, not as an extension: CREATE EXTENSION would fail.
    "init_extension": False,
    # Poll each queue, sleeping 0.1 s when all are empty, so tasks start about as
    # soon as on RabbitMQ. NOTIFY would open one more LISTEN connection per kombu
    # connection, publishers included.
    "wait_time_seconds": 0,
    "polling_interval": 0.1,
}

_clients = {}
_clients_lock = threading.Lock()


@atexit.register
def _close_clients():
    """Close pools before shutdown; psycopg_pool can't join threads after it."""
    for (pid, _), client in _clients.items():
        if pid == os.getpid():
            client.pool.close()


class Channel(pgmq.Channel):
    """PGMQ channel that keeps queue names and bindings as RabbitMQ would."""

    def canonical_queue_name(self, queue_name):
        """Shorten names over 47 characters, keeping them unique.

        Celery's remote control (``celery inspect``) replies on queues named
        ``<uuid>.reply.celery.pidbox``, which PGMQ rejects.
        """
        name = super().canonical_queue_name(queue_name)
        if len(name) <= 47:
            return name
        return f"{name[:30]}_{hashlib.sha1(name.encode()).hexdigest()[:16]}"

    # Virtual transports keep direct-exchange bindings in memory, per connection,
    # so a process that didn't bind the queue itself drops the message: stats
    # events from invenio-queues and Celery's remote-control replies were lost.
    # RabbitMQ and Redis keep bindings in the broker; so does this table.

    def _queue_bind(self, exchange, routing_key, pattern, queue):
        super()._queue_bind(exchange, routing_key, pattern, queue)
        if self.typeof(exchange).type == "direct":
            with self.pgmq.pool.connection() as conn:
                conn.execute(
                    "INSERT INTO pgmq.kombu_bindings VALUES (%s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (exchange, routing_key or "", queue),
                )

    def _delete(self, queue, *args, **kwargs):
        super()._delete(queue, *args, **kwargs)
        with self.pgmq.pool.connection() as conn:
            conn.execute("DELETE FROM pgmq.kombu_bindings WHERE queue = %s", (queue,))

    def _lookup(self, exchange, routing_key, default=None):
        """Fall back to the stored bindings when this connection has none."""
        if exchange and self.typeof(exchange).type == "direct":
            table = self.state.exchanges.get(exchange, {}).get("table", [])
            if not self.typeof(exchange).lookup(table, exchange, routing_key, None):
                with self.pgmq.pool.connection() as conn:
                    rows = conn.execute(
                        "SELECT queue FROM pgmq.kombu_bindings "
                        "WHERE exchange = %s AND routing_key = %s",
                        (exchange, routing_key or ""),
                    ).fetchall()
                if rows:
                    return [queue for (queue,) in rows]
        return super()._lookup(exchange, routing_key, default)


class Transport(pgmq.Transport):
    """kombu's PGMQ transport with defaults for every connection.

    invenio-queues builds a bare ``Connection(BROKER_URL)``, so options set in
    ``CELERY_BROKER_TRANSPORT_OPTIONS`` wouldn't reach the indexer and stats queues.
    """

    Channel = Channel

    def __init__(self, client, **kwargs):
        """Apply the defaults under any explicit options."""
        client.transport_options = {**OPTIONS, **client.transport_options}
        super().__init__(client, **kwargs)

    def _get_pgmq_client(self):
        """One PGMQ client (and connection pool) per process and database.

        kombu's transport makes a client per kombu connection, and Celery and
        invenio-queues keep pools of those: a worker process ended up holding 65
        Postgres connections. ``close_connection`` leaves the shared client open,
        because ``self._pgmq_client`` stays unset.
        """
        key = (os.getpid(), self.client.as_uri(include_password=True))
        with _clients_lock:
            if key not in _clients:
                _clients[key] = self._create_pgmq_client()
            return _clients[key]


TRANSPORT_ALIASES["minipgmq"] = "zenodo_rdm.mini.queues:Transport"


def broker_url(db_uri):
    """Broker URL for the database the app uses."""
    url = make_url(db_uri)
    return url.set(drivername="minipgmq", port=url.port or 5432).render_as_string(
        hide_password=False
    )


def _dsn(url):
    """libpq connection string for a database or broker URL."""
    url = make_url(url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def install(db_uri):
    """Install PGMQ's SQL into the database once; return its version."""
    from pgmq import install_pgmq_from_sql

    dsn = _dsn(db_uri)
    with connect(dsn) as conn:
        installed = conn.execute(
            sql.SQL("SELECT to_regnamespace('pgmq') IS NOT NULL")
        ).fetchone()[0]
    version = "already installed" if installed else install_pgmq_from_sql(dsn=dsn)
    with connect(dsn) as conn:
        # pgmq-py 1.1.4 sends fanout messages (Celery remote control) with
        # send_topic(routing_key, msg, headers), which its bundled SQL lacks.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pgmq.kombu_bindings (exchange text, "
            "routing_key text, queue text, PRIMARY KEY (exchange, routing_key, queue))"
        )
        conn.execute(
            "CREATE OR REPLACE FUNCTION pgmq.send_topic("
            "routing_key text, msg jsonb, headers jsonb) RETURNS integer "
            "LANGUAGE sql AS $$ SELECT pgmq.send_topic(routing_key, msg, headers, 0) $$"
        )
    return version


@worker_init.connect
def release_reserved(sender=None, **kwargs):
    """Make messages a stopped or crashed worker had reserved visible again.

    RabbitMQ requeues unacked messages as soon as the consumer's connection drops;
    PGMQ would hide them for the visibility timeout (30 minutes). Runs before the
    worker consumes, and assumes it is the only worker, as in the mini stack.
    """
    url = sender.app.conf.broker_url
    if not url.startswith("minipgmq://"):
        return
    with connect(_dsn(url), autocommit=True) as conn:
        queues = conn.execute("SELECT queue_name FROM pgmq.meta").fetchall()
        for (name,) in queues:
            conn.execute(
                sql.SQL("UPDATE pgmq.{} SET vt = now() WHERE vt > now()").format(
                    sql.Identifier(f"q_{name}")
                )
            )


@celeryd_after_setup.connect
def start_beat_thread(sender=None, instance=None, **kwargs):
    """Run beat as a thread of the worker when ``ZENODO_BEAT=thread``.

    ``celery worker -B`` forks beat into its own process (outside gevent and
    eventlet pools), which holds one more copy of the app.
    """
    if os.environ.get("ZENODO_BEAT") != "thread":
        return
    beat = EmbeddedService(
        instance.app,
        thread=True,
        schedule_filename=instance.schedule_filename,
        scheduler_cls=instance.scheduler,
    )
    beat.start()
    # Saves the schedule state on shutdown, as the beat process does
    worker_shutdown.connect(lambda **kw: beat.stop(), weak=False)
