# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Migrator tests configuration."""

from pathlib import Path

import jsonlines
import orjson
import pytest
from invenio_rdm_migrator.extract import Extract, Tx
from invenio_rdm_migrator.load.postgresql.transactions import PostgreSQLTx
from invenio_rdm_migrator.load.postgresql.transactions.operations import OperationType
from invenio_rdm_migrator.state import STATE, StateDB
from invenio_rdm_migrator.streams.records.state import ParentModelValidator

from zenodo_rdm_migrator.transform.transactions import ZenodoTxTransform


# FIXME: deduplicate code allowing invenio-rdm-migrator to define re-usable fixtures
@pytest.fixture(scope="function")
def state(tmp_dir):
    """Yields a state.

    Do not call `save` on this fixture. The in memory database will be reset on each
    function, therefore no information will be persisted from test to test.
    """
    state_db = StateDB(
        db_dir=tmp_dir.name, validators={"parents": ParentModelValidator}
    )
    STATE.initialized_state(state_db, cache=False, search_cache=False)

    return STATE


@pytest.fixture(scope="function")
def secret_keys_state(state):
    """Adds secret keys to global state."""
    state.VALUES.add(
        "old_secret_key",
        {"value": bytes("OLDKEY", "utf-8")},
    )
    state.VALUES.add(
        "new_secret_key",
        {"value": bytes("NEWKEY", "utf-8")},
    )
    return


@pytest.fixture(scope="function")
def buckets_state(state):
    """Adds a bucket to draft map to the state."""
    state.BUCKETS.add(
        "0e12b4b6-9cc7-46df-9a04-c11c478de211",
        {"draft_id": "d94f793c-47d2-48e2-9867-ca597b4ebb41"},
    )
    return state


@pytest.fixture(scope="function")
def test_extract_cls():
    """Extract class with customizable tx."""

    class TestExtract(Extract):
        """Test extractor."""

        def __init__(self, txs):
            self.txs = txs if isinstance(txs, list) else [txs]

        def run(self):
            """Yield one element at a time."""
            for tx in self.txs:
                if isinstance(tx, dict):
                    tx = tx
                if isinstance(tx, (str, Path)):
                    tx_path = Path(tx)
                    assert tx_path.exists()
                    with jsonlines.open(tx_path) as tx_ops:
                        tx = {"operations": []}
                        for op in tx_ops:
                            if isinstance(op["key"], str):
                                tx["operations"].append(
                                    {
                                        "key": orjson.loads(op["key"]),
                                        **orjson.loads(op["payload"]),
                                    }
                                )
                            else:
                                tx["operations"].append(
                                    {"key": op["key"], **op["value"]}
                                )
                        # convert "op" to OperationType enum and pop Debezium internals
                        for op in tx["operations"]:
                            op["op"] = OperationType(op["op"].upper())
                            op["key"].pop("__dbz__physicalTableIdentifier", None)
                        # extract the tx_id
                        tx["tx_id"] = tx["operations"][0]["source"]["txId"]
                yield Tx(id=tx["tx_id"], operations=tx["operations"])

    return TestExtract


@pytest.fixture(scope="function")
def pg_tx_load(db_uri, session):
    """Load instance configured with the DB session fixture."""
    return PostgreSQLTx(db_uri, _session=session, dry=False)


@pytest.fixture(scope="function")
def tx_transform():
    """Zenodo Tx transform instance that raises on error."""
    return ZenodoTxTransform(throw=True)
