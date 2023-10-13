# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Invenio-RDM-Migrator is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio RDM migration files actions module."""


from invenio_rdm_migrator.actions import TransformAction
from invenio_rdm_migrator.load.postgresql.transactions.operations import OperationType
from invenio_rdm_migrator.streams.actions import load
from invenio_rdm_migrator.transform.json import JSONTransformMixin


class FileUploadAction(TransformAction):
    """Zenodo to RDM file upload action."""

    name = "file-upload"
    load_cls = load.FileUploadAction

    @classmethod
    def matches_action(cls, tx):
        """Checks if the data corresponds with that required by the action."""
        add_file_ops = [
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.INSERT),
            ("files_files", OperationType.INSERT),
            ("files_object", OperationType.UPDATE),
            ("files_files", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
        ]
        replace_file_ops = [
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.UPDATE),  # Set old OV's is_head = False
            ("files_object", OperationType.INSERT),
            ("files_files", OperationType.INSERT),
            ("files_object", OperationType.UPDATE),
            ("files_files", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
        ]

        ops = tx.as_ops_tuples(
            exclude=(
                # when using a REST API Auth token, it receives an update
                "oauth2server_token",
            ),
        )
        is_file_upload = ops in (add_file_ops, replace_file_ops)
        if is_file_upload:
            # Check if it could be an extra format file
            _, ov = tx.ops_by("files_object", filter_unchanged=False).popitem()
            if ov.get("key") == "application/vnd.plazi.v1+xml":
                # It's an extra format file upload
                return False
            return True
        return False

    def _transform_data(self):
        """Transforms the data and returns an instance of the mapped_cls."""
        _, bucket = self.tx.ops_by("files_bucket").popitem()
        _, file_instance = self.tx.ops_by("files_files").popitem()
        object_versions = self.tx.ops_by(
            "files_object",
            group_id=("bucket_id", "key", "version_id"),
        )

        is_replacement = len(object_versions) == 2
        replaced_object_version = None
        object_version = None
        for ov in object_versions.values():
            if ov.get("is_head") is False:
                replaced_object_version = ov
            else:
                object_version = ov

        if is_replacement:
            assert replaced_object_version is not None

        assert object_version
        fr = {
            "id": None,  # generated by the load action
            "json": {},
            "created": object_version["created"],
            "updated": object_version["updated"],
            "version_id": 1,
            "key": object_version["key"],
            "record_id": None,  # calculated by the load action
            "object_version_id": object_version["version_id"],
        }
        return dict(
            bucket=bucket,
            object_version=object_version,
            replaced_object_version=replaced_object_version,
            file_instance=file_instance,
            file_record=fr,
        )


class FileDeleteAction(TransformAction):
    """Zenodo to RDM file upload action."""

    name = "file-delete"
    load_cls = load.FileDeleteAction

    @classmethod
    def matches_action(cls, tx):
        """Checks if the data corresponds with that required by the action."""
        hard_delete_ops = [
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.DELETE),
        ]

        soft_delete_ops = [
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.UPDATE),
            ("files_object", OperationType.INSERT),  # delete marker
        ]

        ops = tx.as_ops_tuples(
            exclude=(
                # when using a REST API Auth token, it receives an update
                "oauth2server_token",
            ),
        )
        is_file_deletion = ops in (hard_delete_ops, soft_delete_ops)
        if is_file_deletion:
            # Check if it could be an extra format file
            _, ov = tx.ops_by(
                "files_object",
                op_types=["U", "D"],
                filter_unchanged=False,
            ).popitem()
            if ov.get("key") == "application/vnd.plazi.v1+xml":
                # It's an extra format file deletion
                return False
            return True
        return False

    def _transform_data(self):
        """Transforms the data and returns an instance of the mapped_cls."""
        _, bucket = self.tx.ops_by("files_bucket").popitem()
        object_versions = self.tx.ops_by(
            "files_object",
            op_types=["U", "D"],
            group_id=("bucket_id", "key", "version_id"),
        )

        is_soft_delete = len(object_versions) == 2
        delete_marker_object_version = None
        deleted_object_version = None
        if is_soft_delete:
            for ov in object_versions.values():
                if ov.get("file_id") is None:
                    delete_marker_object_version = ov
                else:
                    deleted_object_version = ov
            assert delete_marker_object_version is not None
        else:
            _, deleted_object_version = object_versions.popitem()

        return dict(
            bucket=bucket,
            deleted_object_version=deleted_object_version,
            delete_marker_object_version=delete_marker_object_version,
        )


class MediaFileUploadAction(TransformAction, JSONTransformMixin):
    """Zenodo to RDM media file upload action."""

    name = "media-file-upload"
    load_cls = load.MediaFileUploadAction

    @classmethod
    def matches_action(cls, tx):
        """Checks if the data corresponds with that required by the action."""
        add_file_ops = [
            # NOTE: Extra formats (media files) are only accessible via REST API using
            # tokens, so we take advantage of this for the fingerpinting
            ("oauth2server_token", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.INSERT),
            ("files_files", OperationType.INSERT),
            ("files_object", OperationType.UPDATE),
            ("files_files", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
        ]
        replace_file_ops = [
            # NOTE: Extra formats (media files) are only accessible via REST API using
            # tokens, so we take advantage of this for the fingerpinting
            ("oauth2server_token", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.UPDATE),  # Set old OV's is_head = False
            ("files_object", OperationType.INSERT),
            ("files_files", OperationType.INSERT),
            ("files_object", OperationType.UPDATE),
            ("files_files", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
        ]

        # We might also get the creation of the extra formats bucket
        create_bucket_ops = [
            ("oauth2server_token", OperationType.UPDATE),
            ("files_bucket", OperationType.INSERT),
            ("records_metadata", OperationType.UPDATE),
            ("records_buckets", OperationType.INSERT),
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.INSERT),
            ("files_files", OperationType.INSERT),
            ("files_object", OperationType.UPDATE),
            ("files_files", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
        ]

        ops = tx.as_ops_tuples()
        if ops == create_bucket_ops:
            return True

        is_file_upload = ops in (add_file_ops, replace_file_ops)
        if is_file_upload:
            _, ov = tx.ops_by("files_object", filter_unchanged=False).popitem()
            return ov.get("key") == "application/vnd.plazi.v1+xml"
        return False

    def _transform_data(self):
        """Transforms the data and returns an instance of the mapped_cls."""
        _, bucket = self.tx.ops_by("files_bucket").popitem()
        _, file_instance = self.tx.ops_by("files_files").popitem()
        object_versions = self.tx.ops_by(
            "files_object",
            group_id=("bucket_id", "key", "version_id"),
        )
        pid_value = None
        records = self.tx.ops_by("records_metadata")
        if records:
            _, record = records.popitem()
            pid_value = record["json"]["id"]

        is_replacement = len(object_versions) == 2
        replaced_object_version = None
        object_version = None
        for ov in object_versions.values():
            if ov.get("is_head") is False:
                replaced_object_version = ov
            else:
                object_version = ov

        if is_replacement:
            assert replaced_object_version is not None

        assert object_version
        fr = {
            "id": None,  # generated by the load action
            "json": {},
            "created": object_version["created"],
            "updated": object_version["updated"],
            "version_id": 1,
            "key": object_version["key"],
            "record_id": None,  # calculated by the load action
            "object_version_id": object_version["version_id"],
        }
        return dict(
            bucket=bucket,
            object_version=object_version,
            file_instance=file_instance,
            file_record=fr,
            replaced_object_version=replaced_object_version,
            pid_value=pid_value,
        )


class MediaFileDeleteAction(TransformAction):
    """Zenodo to RDM file upload action."""

    name = "media-file-delete"
    load_cls = load.MediaFileDeleteAction

    @classmethod
    def matches_action(cls, tx):
        """Checks if the data corresponds with that required by the action."""
        hard_delete_ops = [
            # NOTE: Extra formats (media files) are only accessible via REST API using
            # tokens, so we take advantage of this for the fingerpinting
            ("oauth2server_token", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.DELETE),
        ]
        soft_delete_ops = [
            # NOTE: Extra formats (media files) are only accessible via REST API using
            # tokens, so we take advantage of this for the fingerpinting
            ("oauth2server_token", OperationType.UPDATE),
            ("files_bucket", OperationType.UPDATE),
            ("files_object", OperationType.UPDATE),
            ("files_object", OperationType.INSERT),  # delete marker
        ]

        ops = tx.as_ops_tuples()
        is_file_deletion = ops in (hard_delete_ops, soft_delete_ops)
        if is_file_deletion:
            _, ov = tx.ops_by(
                "files_object",
                op_types=["U", "D"],
                filter_unchanged=False,
            ).popitem()
            return ov.get("key") == "application/vnd.plazi.v1+xml"
        return False

    def _transform_data(self):
        """Transforms the data and returns an instance of the mapped_cls."""
        _, bucket = self.tx.ops_by("files_bucket").popitem()
        object_versions = self.tx.ops_by(
            "files_object",
            op_types=["U", "D"],
            group_id=("bucket_id", "key", "version_id"),
        )

        is_soft_delete = len(object_versions) == 2
        delete_marker_object_version = None
        deleted_object_version = None
        if is_soft_delete:
            for ov in object_versions.values():
                if ov.get("file_id") is None:
                    delete_marker_object_version = ov
                else:
                    deleted_object_version = ov
            assert delete_marker_object_version is not None
        else:
            _, deleted_object_version = object_versions.popitem()

        return dict(
            bucket=bucket,
            deleted_object_version=deleted_object_version,
            delete_marker_object_version=delete_marker_object_version,
        )


FILES_ACTIONS = [
    FileUploadAction,
    FileDeleteAction,
    MediaFileUploadAction,
    MediaFileDeleteAction,
]
