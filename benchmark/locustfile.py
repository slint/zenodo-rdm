# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Locust file for a ZenodoRDM instance stress testing.

Usage:

```shell
$ locust --host=http://0.0.0.0 AuthenticatedUser
"""

from locust import HttpUser, task, between
import random
import secrets
import io

# REST API tokens for Auth
USERS = {
    "user1@zenodo.org": "<token-here>",
    "user2@zenodo.org": "<token-here>",
    "user3@zenodo.org": "<token-here>",
    "user4@zenodo.org": "<token-here>",
    "user5@zenodo.org": "<token-here>",
    "user6@zenodo.org": "<token-here>",
    "user7@zenodo.org": "<token-here>",
}


SEARCH_QUERIES = [
    "dataset",
    "article",
    "research",
]

class GuestUser(HttpUser):
    wait_time = between(0.5, 5.0)

    @task
    def api_search(self):
        """API Random search."""
        # We add some random hex to end to possibly bust caches
        params = {"q": f"{random.choice(SEARCH_QUERIES)} OR {secrets.token_hex(16)}"}
        self.client.get("/api/records", params=params)

    def on_start(self):
        self.client.headers = {
            "Accept": "application/json",
            # Randomize user-agent (to bypass rate-limiting)
            "User-Agent": secrets.token_hex(32),
        }


class AuthenticatedUser(HttpUser):
    wait_time = between(0.5, 5.0)

    @task
    def api_create_upload(self):
        self.client.get("/api/user/records")

        recid = None
        # Create the record
        create_resp = self.client.post(
            "/api/records",
            json={
                "access": {"record": "public", "files": "public"},
                "metadata": {
                    "publication_date": "2023-08-01",
                    "publisher": "CERN",
                    "rights": [{"id": "cc-by-4.0"}],
                    "title": "Testing datasets",
                    "creators": [
                        {
                            "person_or_org": {
                                "type": "personal",
                                "family_name": "Anonymous",
                                "given_name": "User",
                            }
                        }
                    ],
                    "resource_type": {"id": "dataset"},
                    "description": "<p>Testing dataset creation</p>",
                },
                "files": {"enabled": True},
            },
        )
        recid = create_resp.json()["id"]

        # Upload a file
        self.client.post(
            f"/api/records/{recid}/draft/files",
            json=[{"key": "data.txt"}],
            name="/api/records/[id]/draft/files",
        )
        self.client.put(
            f"/api/records/{recid}/draft/files/data.txt/content",
            data=io.BytesIO(b"test file upload"),
            name="/api/records/[id]/draft/files/[key]/content",
        )
        self.client.post(
            f"/api/records/{recid}/draft/files/data.txt/commit",
            name="/api/records/[id]/draft/files/[key]/commit",
        )

        # Publish the record
        self.client.post(
            f"/api/records/{recid}/draft/actions/publish",
            name="/api/records/[id]/draft/actions/publish",
        )

        # View the record through the API and UI
        self.client.get(f"/api/records/{recid}", name="/api/records/[id]")
        self.client.get(f"/records/{recid}", name="/records/[id]")


    @task
    def api_search(self):
        """API Random search."""
        params = {"q": f"{random.choice(SEARCH_QUERIES)} OR {secrets.token_hex(16)}"}
        self.client.get("/api/records", params=params, name="/api/records")

    def on_start(self):
        # pick random user credentials
        token = random.choice(list(USERS.values()))
        self.client.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
