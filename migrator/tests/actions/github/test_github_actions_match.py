# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test GitHub actions match."""

from zenodo_rdm_migrator.actions.transform.ignored import GitHubSyncAction


def test_github_release_process(test_extract_cls, tx_transform, tx_files):
    """GitHub release process action match."""
    for f in ("release_process", "release_process2"):
        tx = next(test_extract_cls(tx_files[f]).run())
        match = tx_transform._detect_action(tx)
        assert match == GitHubSyncAction
