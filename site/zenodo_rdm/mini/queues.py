# SPDX-FileCopyrightText: 2026 CERN
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make invenio-queues publish work on kombu's SQLAlchemy transport.

Virtual transports keep exchange-to-queue bindings in memory, per connection.
``invenio_queues.queue.Queue.publish`` only declares the exchange, so on a fresh
connection the queue isn't bound and kombu silently drops the message: stats
events never reach their queues. Declaring the queue on the publishing channel
binds it first. RabbitMQ and Redis keep bindings in the broker, so they don't
need this; it belongs upstream in invenio-queues.
"""

from invenio_queues.queue import Queue
from kombu import Queue as KombuQueue


def publish(self, events):
    """Publish events, declaring (and so binding) the queue first."""
    assert len(events) > 0
    queue = KombuQueue(
        self.routing_key, exchange=self.exchange, routing_key=self.routing_key
    )
    with self.create_producer() as producer:
        for event in events:
            producer.publish(event, declare=[queue])


Queue.publish = publish
