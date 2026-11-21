# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Celery broker and invenio-queues on PGMQ, in the same Postgres.

PGMQ deletes a message when it's acknowledged, so the queue tables stay small
without a cleanup job. It is installed from SQL (``install``), so Postgres needs
no extension files.
"""

import atexit
import os
import threading

from invenio_queues.queue import Queue
from kombu import Queue as KombuQueue
from kombu.transport import TRANSPORT_ALIASES, pgmq
from psycopg import connect, sql
from sqlalchemy.engine import make_url

OPTIONS = {
    # Installed from SQL, not as an extension: CREATE EXTENSION would fail.
    "init_extension": False,
    # Poll each queue, sleeping 1 s when all are empty. NOTIFY would open one
    # more LISTEN connection per kombu connection, publishers included.
    "wait_time_seconds": 0,
    "polling_interval": 1,
}

_clients = {}
_clients_lock = threading.Lock()


@atexit.register
def _close_clients():
    """Close pools before shutdown; psycopg_pool can't join threads after it."""
    for (pid, _), client in _clients.items():
        if pid == os.getpid():
            client.pool.close()


class Transport(pgmq.Transport):
    """kombu's PGMQ transport with defaults for every connection.

    invenio-queues builds a bare ``Connection(BROKER_URL)``, so options set in
    ``CELERY_BROKER_TRANSPORT_OPTIONS`` wouldn't reach the indexer and stats queues.
    """

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


def install(db_uri):
    """Install PGMQ's SQL into the database once; return its version."""
    from pgmq import install_pgmq_from_sql

    dsn = make_url(db_uri).set(drivername="postgresql")
    dsn = dsn.render_as_string(hide_password=False)
    with connect(dsn) as conn:
        installed = conn.execute(
            sql.SQL("SELECT to_regnamespace('pgmq') IS NOT NULL")
        ).fetchone()[0]
    return "already installed" if installed else install_pgmq_from_sql(dsn=dsn)


def publish(self, events):
    """Publish events, declaring (and so binding) the queue first.

    Virtual transports keep exchange-to-queue bindings in memory, per connection.
    ``invenio_queues.queue.Queue.publish`` only declares the exchange, so on a
    fresh connection the queue isn't bound and kombu silently drops the message:
    stats events never reach their queues. RabbitMQ and Redis keep bindings in
    the broker, so they don't need this; it belongs upstream in invenio-queues.
    """
    assert len(events) > 0
    queue = KombuQueue(
        self.routing_key, exchange=self.exchange, routing_key=self.routing_key
    )
    with self.create_producer() as producer:
        for event in events:
            producer.publish(event, declare=[queue])


Queue.publish = publish
