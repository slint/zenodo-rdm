# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Postgres key-value tables standing in for Redis."""

import os
import pickle
import random
from functools import cache

from sqlalchemy import create_engine, exc, text


def engine(uri):
    """Engine shared by the stores of the current process.

    Autocommit, outside Flask-SQLAlchemy's session, so cache writes and locks don't
    wait for (or roll back with) the request transaction. Keyed by pid: Celery
    forks its workers after the app has used the cache, and pooled connections
    shared across processes mix up their replies.
    """
    return _engine(uri, os.getpid())


@cache
def _engine(uri, pid):
    return create_engine(
        uri, isolation_level="AUTOCOMMIT", pool_pre_ping=True, pool_size=2
    )


def create_table(eng, ddl):
    """Create a table on first use; web and worker processes may race to do it."""
    try:
        with eng.connect() as conn:
            conn.execute(text(ddl))
    except exc.IntegrityError, exc.ProgrammingError:
        pass  # created concurrently by another process


class KV:
    """Bytes values with an optional expiry, in one Postgres table."""

    def __init__(self, uri, table, unlogged=True):
        """Create the table if needed."""
        self.uri = uri
        self.table = table
        create_table(
            engine(uri),
            f"CREATE {'UNLOGGED ' if unlogged else ''}TABLE IF NOT EXISTS {table} "
            "(key text PRIMARY KEY, value bytea NOT NULL, expires_at timestamptz)",
        )

    def _run(self, sql, **params):
        with engine(self.uri).connect() as conn:
            return conn.execute(text(sql.format(t=self.table)), params)

    _live = "(expires_at IS NULL OR expires_at > now())"
    _expiry = "CASE WHEN :ttl > 0 THEN now() + make_interval(secs => :ttl) END"

    def get(self, key):
        """Return the value, or None if missing or expired."""
        return self._run(
            f"SELECT value FROM {{t}} WHERE key = :key AND {self._live}", key=key
        ).scalar()

    def set(self, key, value, ttl=None):
        """Store a value; ttl in seconds, None or 0 for no expiry."""
        if random.random() < 0.01:
            self._run("DELETE FROM {t} WHERE expires_at <= now()")
        self._run(
            f"INSERT INTO {{t}} VALUES (:key, :value, {self._expiry}) "
            "ON CONFLICT (key) DO UPDATE "
            "SET value = excluded.value, expires_at = excluded.expires_at",
            key=key,
            value=value,
            ttl=ttl or 0,
        )

    def add(self, key, value, ttl=None):
        """Store a value only if the key is missing or expired. Atomic."""
        return (
            self._run(
                f"INSERT INTO {{t}} VALUES (:key, :value, {self._expiry}) "
                "ON CONFLICT (key) DO UPDATE "
                "SET value = excluded.value, expires_at = excluded.expires_at "
                "WHERE {t}.expires_at <= now() RETURNING key",
                key=key,
                value=value,
                ttl=ttl or 0,
            ).first()
            is not None
        )

    def delete(self, key):
        """Delete a key; True if a live value was there."""
        return (
            self._run(
                f"DELETE FROM {{t}} WHERE key = :key RETURNING {self._live}", key=key
            ).scalar()
            is True
        )

    def has(self, key):
        """Whether a live value exists."""
        return self.get(key) is not None

    def keys(self, prefix=""):
        """Live keys starting with prefix."""
        rows = self._run(
            f"SELECT key FROM {{t}} WHERE starts_with(key, :prefix) AND {self._live}",
            prefix=prefix,
        )
        return [k for (k,) in rows]

    def clear(self, prefix=""):
        """Delete every key starting with prefix."""
        self._run("DELETE FROM {t} WHERE starts_with(key, :prefix)", prefix=prefix)


def dumps(value):
    """Serialize a cache value."""
    return pickle.dumps(value, pickle.HIGHEST_PROTOCOL)


def loads(data):
    """Deserialize a cache value."""
    return None if data is None else pickle.loads(data)
