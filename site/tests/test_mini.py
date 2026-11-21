# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Postgres stand-ins for Redis and RabbitMQ in the mini stack."""

import time

from invenio_queues.queue import Queue
from kombu import Connection, Exchange
from kombu import Queue as KombuQueue
from kombu.pools import connections
from sqlalchemy import text

from zenodo_rdm.mini.backends import PostgresCache, RateLimitStorage
from zenodo_rdm.mini.queues import broker_url, install


def test_cache_add_is_exclusive_until_expiry(app, db):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    web, worker = PostgresCache(uri, "t1:"), PostgresCache(uri, "t1:")
    web.clear()

    assert web.add("lock", "web", timeout=1)
    assert not worker.add("lock", "worker", timeout=1)
    assert worker.get("lock") == "web"
    time.sleep(1.1)
    assert worker.get("lock") is None
    assert worker.add("lock", "worker", timeout=1)
    assert web.delete("lock")
    assert not web.delete("lock")


def test_rate_limit_counts_per_window(app, db):
    storage = RateLimitStorage("mini+" + app.config["SQLALCHEMY_DATABASE_URI"])
    storage.clear("k")

    assert [storage.incr("k", 1) for _ in range(3)] == [1, 2, 3]
    assert storage.get("k") == 3
    time.sleep(1.1)
    assert storage.get("k") == 0
    assert storage.incr("k", 1) == 1


def test_queue_publish_reaches_queue_and_ack_deletes(app, db):
    install(app.config["SQLALCHEMY_DATABASE_URI"])
    url = broker_url(app.config["SQLALCHEMY_DATABASE_URI"])
    queue = Queue(
        Exchange("mini-test", type="direct"),
        "mini-test",
        lambda: connections[Connection(url)],
    )
    # Create and empty the queue on a separate connection, like another process.
    with Connection(url) as conn:
        setup = KombuQueue("mini-test", queue.exchange, "mini-test")
        setup(conn.default_channel).declare()
        setup(conn.default_channel).purge()

    queue.publish([{"n": 1}, {"n": 2}])

    assert [m["n"] for m in queue.consume()] == [1, 2]
    # Consumed messages are gone from the table, not just hidden.
    rows = db.session.execute(text("SELECT count(*) FROM pgmq.q_mini_test"))
    assert rows.scalar() == 0
