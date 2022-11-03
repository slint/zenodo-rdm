import dataclasses
import random
from flask_security.utils import hash_password
from invenio_accounts.proxies import current_datastore
from invenio_db import db
import uuid

from celery import shared_task
from flask import current_app
from flask_principal import Identity, UserNeed
from invenio_access.permissions import any_user, authenticated_user, system_identity
from invenio_communities.generators import CommunityRoleNeed
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.members.records.api import Member
from invenio_communities.proxies import current_communities
from invenio_records_resources.proxies import current_service_registry
from invenio_requests import current_events_service, current_requests_service
from invenio_requests.customizations import CommentEventType
from invenio_rdm_records.proxies import current_rdm_records_service


def get_authenticated_identity(user_id):
    """Return an authenticated identity for the given user."""
    identity = Identity(user_id)
    identity.provides.add(any_user)
    identity.provides.add(UserNeed(user_id))
    identity.provides.add(authenticated_user)
    return identity



RECORD_DATA = {
    "model_data": {
        "created": "2022-10-25 13:18:26.956001",
        "updated": "2022-10-25 14:26:29.707993",
        "version_id": 2,
        "index": 1,
    },
    "service_data": {
        # NOTE: Cannot be passed as input
        # "id": "7186998",
        "pids": {
            "doi": {
                # NOTE: Has to be configured specially
                # "client": "datacite",
                # "provider": "datacite",
                "provider": "external",
                "identifier": "10.5281/zenodo.7186998",
            },
            # NOTE: Cannot be passed as input
            # "oai": {"provider": "oai", "identifier": "oai:zenodo.org:7186998"},
        },
        "access": {
            "files": "public",
            "record": "public",
        },
        "files": {"enabled": False},
        "metadata": {
            "title": "Gene Ontology Data Archive",
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "given_name": "Chris",
                        "family_name": "Mungall",
                        "affiliations": [
                            {"name": "Lawrence Berkeley National Laboratory"}
                        ],
                        "identifiers": [
                            {"scheme": "orcid", "identifier": "0000-0002-6601-2165"}
                        ],
                    }
                },
            ],
            "description": "<p>Archival bundle of GO data release.</p>",
            "resource_type": {"id": "dataset"},
            "publication_date": "2018-07-02",
            "rights": [{"id": "cc-by-4.0"}],
        },
    },
    # TODO: We somehow need to pass the parent ID
    # "parent": { "id": "1205166", },
    # TODO: We somehow pass the identity (to be the owner)
    "identity": {"user": 12345},
}


ALL_RECORDS = [
    RECORD_DATA
    for _ in range(100)
]

def chunkify(iterable, n):
    import itertools
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def bulk_create_record(data):
    from invenio_records_resources.services.uow import UnitOfWork
    from datetime import datetime
    def _create_record(d, uow=None):
        service = current_rdm_records_service
        d['service_data']['pids']['doi']['identifier'] = f'10.5281/zenodo.{uuid.uuid4()}'
        identity = get_authenticated_identity(d["identity"]["user"])
        draft = service.create(data=d["service_data"], identity=identity, uow=uow)
        service.publish(id_=draft.id, identity=identity, uow=uow)

    start = datetime.now()
    print('start', start.isoformat())
    for d_chunk in chunkify(data, 20):
        with UnitOfWork() as uow:
            for d in d_chunk:
                print('record', datetime.now().isoformat())
                _create_record(d, uow=uow)
            uow.commit()
        print('chunk', datetime.now().isoformat())
    end = datetime.now()
    print('end', end.isoformat())
    print('total', (end - start))


# str 2022-11-02T16:33:48.252068
# end 2022-11-02T16:35:21.642678

def bulk_create_user(data):
    """Load a single user."""
    user_data = {
        "email": data.pop("email"),
        "active": data.get("active", False),
        "password": hash_password('123456'),
        "username": data.get("username"),
        "user_profile": dict(full_name=data.get("full_name", ""), affiliations=data.get("affiliations", "")),
    }

    current_datastore.create_user(**user_data)
    db.session.commit()
