# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ignored actions match."""

import pytest

from zenodo_rdm_migrator.actions.transform.ignored import BucketNoop, GitHubSyncAction


@pytest.fixture()
def test_github_sync(test_extract_cls, tx_transform, tx_files):
    """GitHub Sync action match."""
    tx = next(test_extract_cls(tx_files["repo_udpate"]).run())
    match = tx_transform._detect_action(tx)
    assert match == GitHubSyncAction


@pytest.fixture()
def test_bucket_noop(test_extract_cls, tx_transform, tx_files):
    """Bucket no-op action match."""
    tx = next(test_extract_cls(tx_files["bucket-noop"]).run())
    match = tx_transform._detect_action(tx)
    assert match == BucketNoop
