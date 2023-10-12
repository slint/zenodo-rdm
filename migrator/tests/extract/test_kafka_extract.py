# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Migrator tests configuration."""

import itertools
import random
from collections import Counter
from unittest.mock import PropertyMock

from invenio_rdm_migrator.extract import Tx
from invenio_rdm_migrator.load.postgresql.transactions.operations import OperationType

from zenodo_rdm_migrator.extract import KafkaExtract, KafkaExtractEnd


def _random_chunks(li, min_chunk=1, max_chunk=50):
    it = iter(li)
    while True:
        nxt = list(itertools.islice(it, random.randint(min_chunk, max_chunk)))
        if nxt:
            yield nxt
        else:
            break


class MockConsumer(list):
    """Mock Kafka consumer iterator."""

    def commit(self):
        pass


def _patch_consumers(mocker, tx_info, ops):
    """Helper for patching consumers of ``KafkaExtract``."""
    mocker.patch.object(
        KafkaExtract,
        "_tx_consumer",
        side_effect=[*tx_info, MockConsumer([]), KafkaExtractEnd],
        new_callable=PropertyMock,
    )
    mocker.patch.object(
        KafkaExtract,
        "_ops_consumer",
        side_effect=[*ops, MockConsumer([]), KafkaExtractEnd],
        new_callable=PropertyMock,
    )


LAST_TX_COMMIT_LSN = 1461029027816
LATER_LAST_TX_COMMIT_LSN = 1461027893600
OLDEST_ACTIVE_TX = 563388920

FIRST_TX_OP_COUNTS = (
    563389016,
    {
        "public.oauth2server_token": 1,
        "public.records_metadata": 1,
    },
)
LAST_TX_OP_COUNTS = (
    563390849,
    {
        "public.pidstore_pid": 8,
        "public.files_bucket": 5,
        "public.records_metadata": 3,
        "public.files_files": 2,
        "public.files_object": 2,
        "public.records_buckets": 1,
        "public.communities_community_record": 1,
        "public.pidstore_redirect": 1,
        "public.pidrelations_pidrelation": 1,
    },
)
MIDDLE_TX_OP_COUNTS = (
    563390343,
    {
        "public.files_bucket": 2,
        "public.files_files": 2,
        "public.files_object": 2,
        "public.oauth2server_token": 1,
        "public.records_metadata": 1,
    },
)


def _assert_op_counts(tx, expected_counts):
    op_counts = Counter(
        [f'{op["source"]["schema"]}.{op["source"]["table"]}' for op in tx.operations]
    )
    assert op_counts == expected_counts


def _assert_result(
    result,
    *,
    count,
    first_tx_id,
    last_tx_id,
    extra_tx_ids=None,
    excluded_tx_ids=None,
    tx_op_counts=None,
):
    assert len(result) == count
    assert all(isinstance(t, Tx) for t in result)
    assert all(
        all(isinstance(o["op"], OperationType) for o in t.operations) for t in result
    )
    tx_dict = {t.id: t for t in result}
    tx_lsn_list = [(t.id, t.commit_lsn) for t in result]
    assert tx_lsn_list == sorted(tx_lsn_list, key=lambda x: x[1])
    assert tx_lsn_list[0][0] == first_tx_id
    assert tx_lsn_list[-1][0] == last_tx_id
    assert set(extra_tx_ids or []) <= set(tx_lsn_list)
    assert (
        len(set(excluded_tx_ids or []).intersection({t for t, _ in tx_lsn_list})) == 0
    )
    for tx_id, op_counts in (tx_op_counts or {}).items():
        _assert_op_counts(tx_dict[tx_id], op_counts)


def test_kafka_data(kafka_data):
    """Test sample data basic attributes."""
    assert len(kafka_data.ops) == 1820
    assert len(kafka_data.tx_info) == 282


def test_simple_extract(mocker, kafka_data):
    """Test a simple run over a single uninterrupted iteration of messages.

    "Uninterrupted" means that the Kafka consumers yield all the available messages on
    their first iteration. This is not a very realistic scenario, since normally
    messages arrive in random-sized batches to Kafka topics, and are consumed in a
    somewhat "messy" order. It still serves as a good base case.
    """
    _patch_consumers(
        mocker,
        [MockConsumer(kafka_data.tx_info)],
        [MockConsumer(kafka_data.ops)],
    )

    extract = KafkaExtract(
        ops_topic="test_topic",
        tx_topic="test_topic",
        # This Tx commit LSN has a few commited Tx before it
        last_tx_commit_lsn=LAST_TX_COMMIT_LSN,
        # We skip a couple of Tx
        oldest_active_xid=OLDEST_ACTIVE_TX,
    )
    result = list(extract.run())
    _assert_result(
        result,
        count=122,
        first_tx_id=563389016,
        last_tx_id=563390849,
        excluded_tx_ids=(563388795,),
        tx_op_counts=dict([FIRST_TX_OP_COUNTS, MIDDLE_TX_OP_COUNTS, LAST_TX_OP_COUNTS]),
    )


def test_randomized_extract(mocker, kafka_data):
    """Test single uninterrupted iteration of random order messages.

    This should work since in the context of a single run, the order of transactions is
    maintained.
    """
    shuffled_tx_info = random.sample(kafka_data.tx_info, len(kafka_data.tx_info))
    shuffled_ops = random.sample(kafka_data.ops, len(kafka_data.ops))
    _patch_consumers(
        mocker,
        [MockConsumer(shuffled_tx_info)],
        [MockConsumer(shuffled_ops)],
    )

    extract = KafkaExtract(
        ops_topic="test_topic",
        tx_topic="test_topic",
        last_tx_commit_lsn=LAST_TX_COMMIT_LSN,
        oldest_active_xid=OLDEST_ACTIVE_TX,
    )
    result = list(extract.run())
    _assert_result(
        result,
        count=122,
        first_tx_id=563389016,
        last_tx_id=563390849,
        excluded_tx_ids=(563388795,),
        tx_op_counts=dict([FIRST_TX_OP_COUNTS, MIDDLE_TX_OP_COUNTS, LAST_TX_OP_COUNTS]),
    )


def test_random_sized_batches_extract(mocker, kafka_data):
    """Test random-sized batches of messages.

    Here we randomize the number of messages returned by each consumer. This is fine as
    long as we don't end up in a scenario where a very old transaction comes out of
    order (specifically >=10 transactions later)

    In theory this can be avoided though by setting the ``tx_buffer`` option of
    ``KafkaExtract`` to a higher value.
    """
    # NOTE: We create the same number of total batches for both types
    tx_info_batches, ops_batches = zip(
        *itertools.zip_longest(
            [MockConsumer(c) for c in _random_chunks(kafka_data.tx_info)],
            [MockConsumer(c) for c in _random_chunks(kafka_data.ops)],
            fillvalue=MockConsumer([]),
        )
    )
    _patch_consumers(
        mocker,
        tx_info_batches,
        ops_batches,
    )
    extract = KafkaExtract(
        ops_topic="test_topic",
        tx_topic="test_topic",
        last_tx_commit_lsn=LAST_TX_COMMIT_LSN,
        oldest_active_xid=OLDEST_ACTIVE_TX,
    )
    result = list(extract.run())
    _assert_result(
        result,
        count=122,
        first_tx_id=563389016,
        last_tx_id=563390849,
        excluded_tx_ids=(563388795,),
        tx_op_counts=dict([FIRST_TX_OP_COUNTS, MIDDLE_TX_OP_COUNTS, LAST_TX_OP_COUNTS]),
    )


def test_later_last_commit_lsn(mocker, kafka_data):
    """Test passing a later transaction ID from the stream.

    In this case we should just get less transactions processed, but still they should
    be whole (since we go through all messages, but just discard any that have a
    smaller transaction ID).
    """
    _patch_consumers(
        mocker,
        [MockConsumer(kafka_data.tx_info)],
        [MockConsumer(kafka_data.ops)],
    )

    extract = KafkaExtract(
        ops_topic="test_topic",
        tx_topic="test_topic",
        # a later transaction in the file
        last_tx_commit_lsn=LATER_LAST_TX_COMMIT_LSN,
        oldest_active_xid=OLDEST_ACTIVE_TX,
    )
    result = list(extract.run())
    _assert_result(
        result,
        count=129,
        first_tx_id=563388920,
        last_tx_id=563390849,
        excluded_tx_ids=(563388910,),
        tx_op_counts=dict([MIDDLE_TX_OP_COUNTS, LAST_TX_OP_COUNTS]),
    )
