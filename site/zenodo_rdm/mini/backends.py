# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Cache, session, identity-cache and rate-limit backends on Postgres."""

import time

from flask import current_app
from flask_caching.backends.base import BaseCache
from flask_oauthlib.contrib.cache import Cache as OAuthCache
from invenio_communities.cache.cache import IdentityCache
from limits.storage import MovingWindowSupport, Storage
from simplekv import FOREVER, NOT_SET, KeyValueStore, TimeToLiveMixin
from sqlalchemy import exc, text

from .store import KV, create_table, dumps, engine, loads


class PostgresCache(BaseCache):
    """Flask-Caching backend (``CACHE_TYPE``) in an unlogged table.

    ``add`` is atomic, so ``invenio_cache.lock.CachedMutex`` locks hold across
    processes, as they do on Redis.
    """

    def __init__(self, uri, key_prefix="", default_timeout=300, **_):
        """Initialize; other Flask-Caching options don't apply."""
        super().__init__(default_timeout=default_timeout)
        self.kv = KV(uri, "zenodo_mini_cache")
        self.key_prefix = key_prefix

    @classmethod
    def factory(cls, app, config, args, kwargs):
        """Build from the app config."""
        kwargs.setdefault("key_prefix", config.get("CACHE_KEY_PREFIX") or "")
        return cls(app.config["SQLALCHEMY_DATABASE_URI"], *args, **kwargs)

    def get(self, key):
        """Get a value."""
        return loads(self.kv.get(self.key_prefix + key))

    def set(self, key, value, timeout=None):
        """Set a value."""
        ttl = self._normalize_timeout(timeout)
        self.kv.set(self.key_prefix + key, dumps(value), ttl)
        return True

    def add(self, key, value, timeout=None):
        """Set a value only if the key is not set."""
        ttl = self._normalize_timeout(timeout)
        return self.kv.add(self.key_prefix + key, dumps(value), ttl)

    def delete(self, key):
        """Delete a key."""
        return self.kv.delete(self.key_prefix + key)

    def has(self, key):
        """Whether the key is set."""
        return self.kv.has(self.key_prefix + key)

    def clear(self):
        """Delete all keys with this cache's prefix."""
        self.kv.clear(self.key_prefix)
        return True


class IdentityPostgresCache(IdentityCache):
    """``COMMUNITIES_IDENTITIES_CACHE_HANDLER`` replacing the Redis-only default."""

    def __init__(self, app=None):
        """Initialize."""
        super().__init__(app=app)
        app = app or current_app
        prefix = app.config.get("COMMUNITIES_IDENTITIES_CACHE_REDIS_PREFIX", "identity")
        self.cache = PostgresCache(
            app.config["SQLALCHEMY_DATABASE_URI"], key_prefix=f"{prefix}:"
        )

    def get(self, key):
        """Get a value."""
        return self.cache.get(key)

    def set(self, key, value, timeout=None):
        """Set a value."""
        self.cache.set(key, value, timeout=timeout or self.timeout)

    def delete(self, key):
        """Delete a key."""
        self.cache.delete(key)

    def flush(self):
        """Delete all identities."""
        self.cache.clear()

    def append(self, key, value):
        """Append a value to a stored list, like the Redis handler."""
        values = self.cache.get(key) or []
        if value not in values:
            values.append(value)
        self.set(key, values)


class SessionStore(TimeToLiveMixin, KeyValueStore):
    """simplekv store for Flask-KVSession: only what Flask-KVSession calls.

    simplekv's own ``SQLAlchemyStore`` uses the SQLAlchemy 1.x API and fails on 2.x.
    """

    def __init__(self, uri):
        """Initialize."""
        self.kv = KV(uri, "zenodo_mini_sessions")

    def _has_key(self, key):
        return self.kv.has(key)

    def _delete(self, key):
        self.kv.delete(key)

    def _get(self, key):
        value = self.kv.get(key)
        if value is None:
            raise KeyError(key)
        return bytes(value)

    def _put(self, key, data, ttl_secs=NOT_SET):
        ttl = None if ttl_secs in (NOT_SET, FOREVER) else ttl_secs
        self.kv.set(key, data, ttl)
        return key


def session_store_factory(app):
    """``ACCOUNTS_SESSION_STORE_FACTORY`` for the Postgres session store."""
    return SessionStore(app.config["SQLALCHEMY_DATABASE_URI"])


class RateLimitStorage(Storage, MovingWindowSupport):
    """``limits`` storage with moving windows, the strategy production uses.

    Fixed-window counters restart in place on the next hit. Moving-window hits are
    rows with a timestamp, checked and added under a per-key advisory lock.

    Registered for URIs like ``mini+postgresql+psycopg2://...``.
    """

    STORAGE_SCHEME = ("mini+postgresql", "mini+postgresql+psycopg2")

    def __init__(self, uri, wrap_exceptions=False, **options):
        """Initialize."""
        super().__init__(uri, wrap_exceptions=wrap_exceptions, **options)
        self.uri = uri.removeprefix("mini+")
        create_table(
            engine(self.uri),
            "CREATE UNLOGGED TABLE IF NOT EXISTS zenodo_mini_ratelimit "
            "(key text PRIMARY KEY, count bigint NOT NULL, "
            "expires_at timestamptz NOT NULL)",
        )
        create_table(
            engine(self.uri),
            "CREATE UNLOGGED TABLE IF NOT EXISTS zenodo_mini_ratelimit_hits "
            "(key text NOT NULL, at timestamptz NOT NULL)",
        )
        create_table(
            engine(self.uri),
            "CREATE INDEX IF NOT EXISTS zenodo_mini_ratelimit_hits_key "
            "ON zenodo_mini_ratelimit_hits (key, at)",
        )

    @property
    def base_exceptions(self):
        """Errors the storage may raise."""
        return exc.SQLAlchemyError

    def _run(self, sql, fetch=lambda r: None, **params):
        # Fetch before the connection goes back to the pool (see KV._run).
        with engine(self.uri).connect() as conn:
            return fetch(conn.execute(text(sql), params))

    def incr(self, key, expiry, amount=1):
        """Increment the counter, starting a new window if it expired."""
        return self._run(
            "INSERT INTO zenodo_mini_ratelimit AS r "
            "VALUES (:key, :amount, now() + make_interval(secs => :expiry)) "
            "ON CONFLICT (key) DO UPDATE SET "
            "count = CASE WHEN r.expires_at <= now() THEN excluded.count "
            "ELSE r.count + excluded.count END, "
            "expires_at = CASE WHEN r.expires_at <= now() THEN excluded.expires_at "
            "ELSE r.expires_at END "
            "RETURNING count",
            fetch=lambda r: r.scalar(),
            key=key,
            amount=amount,
            expiry=expiry,
        )

    def get(self, key):
        """Current counter value."""
        return (
            self._run(
                "SELECT count FROM zenodo_mini_ratelimit "
                "WHERE key = :key AND expires_at > now()",
                fetch=lambda r: r.scalar(),
                key=key,
            )
            or 0
        )

    def get_expiry(self, key):
        """Window end as a Unix timestamp."""
        value = self._run(
            "SELECT extract(epoch FROM coalesce(max(expires_at), now())) "
            "FROM zenodo_mini_ratelimit WHERE key = :key",
            fetch=lambda r: r.scalar(),
            key=key,
        )
        return float(value)

    def acquire_entry(self, key, limit, expiry, amount=1):
        """Record a hit if fewer than ``limit`` happened in the last ``expiry`` s."""
        if amount > limit:
            return False
        params = {"key": key, "expiry": expiry, "amount": amount}
        with engine(self.uri).connect() as conn:

            def run(sql):
                return conn.execute(text(sql), params)

            run("SELECT pg_advisory_lock(hashtext(:key))")
            try:
                run(
                    "DELETE FROM zenodo_mini_ratelimit_hits WHERE key = :key "
                    "AND at <= clock_timestamp() - make_interval(secs => :expiry)"
                )
                count = run(
                    "SELECT count(*) FROM zenodo_mini_ratelimit_hits WHERE key = :key"
                ).scalar()
                if count + amount > limit:
                    return False
                run(
                    "INSERT INTO zenodo_mini_ratelimit_hits "
                    "SELECT :key, clock_timestamp() FROM generate_series(1, :amount)"
                )
                return True
            finally:
                run("SELECT pg_advisory_unlock(hashtext(:key))")

    def get_moving_window(self, key, limit, expiry):
        """Start of the window (oldest live hit) and the number of live hits."""
        start, count = self._run(
            "SELECT extract(epoch FROM min(at)), count(*) "
            "FROM zenodo_mini_ratelimit_hits WHERE key = :key "
            "AND at > clock_timestamp() - make_interval(secs => :expiry)",
            fetch=lambda r: r.first(),
            key=key,
            expiry=expiry,
        )
        return (float(start), count) if count else (time.time(), 0)

    def check(self):
        """Whether the database answers."""
        try:
            return self._run("SELECT 1", fetch=lambda r: r.scalar()) == 1
        except exc.SQLAlchemyError:
            return False

    def reset(self):
        """Delete all counters."""
        self._run("DELETE FROM zenodo_mini_ratelimit_hits")
        return self._run(
            "DELETE FROM zenodo_mini_ratelimit", fetch=lambda r: r.rowcount
        )

    def clear(self, key):
        """Delete one counter."""
        self._run("DELETE FROM zenodo_mini_ratelimit WHERE key = :key", key=key)
        self._run("DELETE FROM zenodo_mini_ratelimit_hits WHERE key = :key", key=key)


def _oauth2_cache(self, **kwargs):
    """``OAUTH2_CACHE_TYPE = "mini"``: OAuth2 grant codes in the Postgres cache.

    Flask-OAuthlib picks its cache by method name and has no plug-in point, so the
    method is added here; otherwise grant codes would live in one process only.
    """
    uri = self.config["SQLALCHEMY_DATABASE_URI"]
    return PostgresCache(uri, key_prefix="oauth2:", **kwargs)


OAuthCache._mini = _oauth2_cache
