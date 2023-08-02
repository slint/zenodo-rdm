# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Locust file for a ZenodoRDM instance stress testing.

Usage:
.. code-block:: console
  $ pip install locust

.. code-block:: console
  $ locust -f tests/locust/locustfile.py --host=http://0.0.0.0
  [2017-12-19 12:56:37,173] 127.0.0.1/INFO/locust.main: Starting web monitor \
  at *:8089
  [2017-12-19 12:56:37,175] 127.0.0.1/INFO/locust.main: Starting Locust 0.8
  ...
  $ firefox http://127.0.0.1:8089

If you need to run an specific set of tests:
.. code-block:: console
   $ locust -f tests/locust/locustfile.py Records --host=http://0.0.0.0
  [2017-12-19 12:56:37,173] 127.0.0.1/INFO/locust.main: Starting web monitor \
  at *:8089
  [2017-12-19 12:56:37,175] 127.0.0.1/INFO/locust.main: Starting Locust 0.8
  ...
  $ firefox http://127.0.0.1:8089
"""

from locust import FastHttpUser, HttpUser, task, between
import random
import secrets
import io


"""
# Anonymous
- view record
- download file
- search

# Logged-in
- create record
- upload file(s)
- edit metadata
- publish record
- view created record
- (edit record?)
"""


USERS = {
    # "user3@zenodo.org": "VrZgOGfdsycALotzS3sWIx1BSUsM9ip1HKYiY4a4WKXJ505BKsaIKNRKEcI7",
    # "user4@zenodo.org": "Tr0FxEVRs42C73T6oASBU4aSc0XbswyKSKaZsojeqmivDj9NZmCX7FNt4BkO",
    # "user5@zenodo.org": "vMxXaKDsCFSkNgV9DWSwy3yPnMNy54IJHFkY2GPKWeva7pMvHpqfF0ALGonU",
    # "user6@zenodo.org": "v4dqEgkKKvnjiRzRQOFqKhbCGLDVSRdka8dl5voh95i4HZ6fMEGx0ZKyKLb3",
    # "user7@zenodo.org": "YnpgXurvW8ZcYlA8E76ULIwhDkwnpgsUu14mxmskgC5BdAZmJYaZj8DHTVBT",
    "prod-user": "yJ6mEW65POupErknDGcJWgWtBNOG5C490RU7pmvPjbOOLD529bdeo0XG9Pon",
}


SEARCH_QUERIES = [
    "dataset",
    "article",
    "research",
]


class GuestUser(HttpUser):
    wait_time = between(0.5, 5.0)

    @task
    def api_search_random(self):
        """API Random search."""
        params = {"q": f"{random.choice(SEARCH_QUERIES)} OR {secrets.token_hex(16)}"}
        self.client.get("/api/records", params=params)


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


    @task(0)
    def api_search_random(self):
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
