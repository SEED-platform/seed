"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.utils.cache import set_cache_raw
from seed.utils.organizations import create_organization


class CacheEntryViewTests(TestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user, "my org")
        self.other_org, _, _ = create_organization(User.objects.create_user(username="other_user@demo.com"), "other org")
        self.client.login(**user_details)

    def _get(self, unique_id):
        return self.client.get(reverse("api:v3:cache_entries-detail", args=[unique_id]) + f"?organization_id={self.org.id}")

    def test_retrieve_own_task_result(self):
        # task results are keyed by the org ID and a 5-digit random number (e.g., `start_export`)
        set_cache_raw(f"{self.org.id}12345", {"data": "exported"})

        response = self._get(f"{self.org.id}12345")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": "exported"})

    def test_superuser_retrieves_task_result_of_any_org(self):
        # `has_perm` lets superusers access organizations they are not members of
        superuser_details = {"username": "superuser@demo.com", "password": "test_pass", "email": "superuser@demo.com"}
        User.objects.create_superuser(**superuser_details)
        self.client.login(**superuser_details)
        set_cache_raw(f"{self.org.id}12345", {"data": "exported"})

        response = self._get(f"{self.org.id}12345")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": "exported"})

    def test_retrieve_other_cache_entries_is_denied(self):
        set_cache_raw(f"{self.other_org.id}12345", {"data": "other org export"})
        set_cache_raw(f"access_token_{self.other_org.id}", {"token": "secret"})

        for unique_id in (f"{self.other_org.id}12345", f"access_token_{self.other_org.id}"):
            response = self._get(unique_id)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"error": "No data found for the provided unique_id"})
