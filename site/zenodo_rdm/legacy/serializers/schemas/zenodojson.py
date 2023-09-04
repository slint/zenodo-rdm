# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# Zenodo is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Zenodo serializer schemas."""

from marshmallow import Schema, fields, missing, post_dump, pre_dump
from marshmallow_utils.fields import EDTFDateString, SanitizedHTML, SanitizedUnicode

from . import common


class ResourceTypeSchema(Schema):
    """Resource type schema."""

    type = fields.Str()
    subtype = fields.Str()
    title = fields.Str(attribute="title.en")


class JournalSchema(Schema):
    """Schema for a journal."""

    issue = fields.Str()
    pages = fields.Str()
    title = fields.Str()
    volume = fields.Str()
    year = fields.Str()


class MeetingSchema(Schema):
    """Schema for a meeting."""

    title = fields.Str()
    acronym = fields.Str()
    dates = fields.Str()
    place = fields.Str()
    url = fields.Str()
    session = fields.Str()
    session_part = fields.Str()


class ImprintSchema(Schema):
    """Schema for imprint."""

    publisher = fields.Str()
    place = fields.Str()
    isbn = fields.Str()


class PartOfSchema(Schema):
    """Schema for imprint."""

    pages = fields.Str()
    title = fields.Str()


class ThesisSchema(Schema):
    """Schema for thesis."""

    university = fields.Str()
    supervisors = fields.Nested(common.CreatorSchema, many=True)


class FunderSchema(Schema):
    """Schema for a funder."""

    doi = fields.Str()
    name = fields.Str(dump_only=True)
    acronyms = fields.List(fields.Str(), dump_only=True)
    links = fields.Method("get_funder_url", dump_only=True)

    def get_funder_url(self, obj):
        """Get grant url."""
        return dict(self=common.api_link_for("funder", id=obj["doi"]))


class GrantSchema(Schema):
    """Schema for a grant."""

    title = fields.Str(dump_only=True)
    code = fields.Str()
    program = fields.Str(dump_only=True)
    acronym = fields.Str(dump_only=True)
    funder = fields.Nested(FunderSchema)
    links = fields.Method("get_grant_url", dump_only=True)

    def get_grant_url(self, obj):
        """Get grant url."""
        return dict(self=common.api_link_for("grant", id=obj["internal_id"]))


class FilesSchema(Schema):
    """Files metadata schema."""

    type = fields.String()
    checksum = fields.String()
    size = fields.Integer()
    bucket = fields.String()
    key = fields.String()
    links = fields.Method("get_links")

    def get_links(self, obj):
        """Get links."""
        return {
            "self": common.api_link_for("object", bucket=obj["bucket"], key=obj["key"])
        }


class MetadataSchema(common.MetadataSchema):
    """Metadata schema for a record."""

    resource_type = fields.Nested(ResourceTypeSchema)
    access_right_category = fields.Method("dump_access_right_category", dump_only=True)

    journal = fields.Nested(JournalSchema, attribute="custom_fields.journal:journal")
    meeting = fields.Nested(MeetingSchema, attribute="custom_fields.meeting:meeting")
    imprint = fields.Nested(ImprintSchema, attribute="custom_fields.imprint:imprint")
    part_of = fields.Nested(PartOfSchema, attribute="custom_fields.part_of:part_of")
    thesis = fields.Nested(ThesisSchema, attribute="custom_fields.thesis:thesis")

    alternate_identifiers = fields.Method("dump_alternate_identifiers")

    license = fields.Nested({"id": fields.Function(lambda x: x)})
    grants = fields.Nested(GrantSchema, many=True)
    communities = fields.Method("dump_communities")
    relations = fields.Method("dump_relations")

    def dump_communities(self, obj):
        """Dump communities."""
        community_slugs = obj.get("_communities", [])
        if community_slugs:
            return [{"id": c} for c in community_slugs]
        return missing

    def dump_alternate_identifiers(self, obj):
        result = []
        rel_id_schema = common.RelatedIdentifierSchema(exclude=("relation",))
        alternate_identifiers = obj.get("identifiers", [])
        for identifier in alternate_identifiers:
            result.append(
                rel_id_schema.dump(
                    {
                        "relation_type": {"id": "isAlternateIdentifier"},
                        "identifier": identifier["identifier"],
                    }
                )
            )
        return result or missing

    def dump_access_right_category(self, obj):
        """Get access right category."""
        ACCESS_RIGHT_CATEGORY = {
            "open": "success",
            "embargoed": "warning",
            "restricted": "danger",
            "closed": "danger",
        }
        # TODO: Fix
        return ACCESS_RIGHT_CATEGORY["open"]

    def dump_relations(self, obj):
        """Dump the relations to a dictionary."""
        # TODO: Figure out
        return {
            "version": [
                {
                    "index": obj["versions"]["index"] - 1,
                    "is_last": obj["versions"]["is_latest"],
                    # "count": 1,
                    # "last_child": {"pid_type": "recid", "pid_value": "1235426"},
                    # "parent": {"pid_type": "recid", "pid_value": "1235425"},
                }
            ]
        }


class StatsSchema(Schema):
    """Schema for usage statistics."""

    downloads = fields.Integer(attribute="all_versions.downloads")
    unique_downloads = fields.Integer(attribute="all_versions.unique_downloads")
    views = fields.Integer(attribute="all_versions.views")
    unique_views = fields.Integer(attribute="all_versions.unique_views")
    volume = fields.Integer(attribute="all_versions.volume")

    version_downloads = fields.Integer(attribute="this_version.downloads")
    version_unique_downloads = fields.Integer(attribute="this_version.unique_downloads")
    version_unique_views = fields.Integer(attribute="this_version.unique_views")
    version_views = fields.Integer(attribute="this_version.views")
    version_volume = fields.Integer(attribute="this_version.volume")


class ZenodoSchema(common.LegacySchema):
    """Schema for Zenodo records v1."""

    created = SanitizedUnicode()
    updated = SanitizedUnicode()
    recid = SanitizedUnicode(attribute="id", dump_only=True)
    revision = fields.Integer(attribute="revision_id")

    files = fields.Nested(FilesSchema, many=True, dump_only=True, attribute="files")
    metadata = fields.Nested(MetadataSchema)

    owners = fields.Method("dump_owners")

    def dump_owners(self, obj):
        """Dump owners."""
        return [{"id": obj["parent"]["access"]["owned_by"]["user"]}]

    updated = fields.Str(dump_only=True)

    status = fields.Method("dump_status")

    def dump_status(self, obj):
        """Dump status."""
        if obj["is_draft"]:
            return "draft"
        return "published"

    stats = fields.Nested(StatsSchema)
