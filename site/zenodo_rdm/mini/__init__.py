# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Opt-in "mini" stack: Postgres replaces Redis and RabbitMQ.

Enabled with ``ZENODO_STACK=mini`` (see ``invenio.cfg`` and ``docker-compose.mini.yml``).
Not meant for production: the full stack stays the default.
"""
