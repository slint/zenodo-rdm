# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Mini stack housekeeping tasks."""

from celery import shared_task
from invenio_db import db
from sqlalchemy import text


@shared_task(ignore_result=True)
def purge_broker_messages():
    """Delete consumed broker messages.

    kombu's SQLAlchemy transport marks delivered messages invisible but never
    deletes them, so the table would grow forever.
    """
    db.session.execute(
        text(
            "DELETE FROM kombu_message "
            "WHERE NOT visible AND timestamp < now() - interval '1 hour'"
        )
    )
    db.session.commit()
