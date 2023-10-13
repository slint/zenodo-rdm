# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test draft actions match."""

import pytest

from zenodo_rdm_migrator.actions.transform.drafts import DraftEditAction
from zenodo_rdm_migrator.actions.transform.files import MediaFileUploadAction


@pytest.fixture()
def test_draft_update(test_extract_cls, tx_transform, tx_files):
    """Draft update action match."""
    tx = next(test_extract_cls(tx_files["update2"]).run())
    match = tx_transform._detect_action(tx)
    assert match == DraftEditAction


@pytest.fixture()
def test_media_file_upload(test_extract_cls, tx_transform, tx_files):
    """Draft update action match."""
    tx = next(test_extract_cls(tx_files["media-file-upload"]).run())
    match = tx_transform._detect_action(tx)
    assert match == MediaFileUploadAction
