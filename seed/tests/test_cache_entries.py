"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_VIEWER
from seed.models import Column
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.cache import is_task_result_id, new_task_result_id, set_cache_raw, set_task_result
from seed.utils.organizations import create_organization

NOT_FOUND = {"error": "No data found for the provided unique_id"}


class CacheEntryViewTests(TestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user, "my org")
        self.other_org, _, _ = create_organization(User.objects.create_user(username="other_user@demo.com"), "other org")
        self.client.login(**user_details)
        # task results are keyed by the organization ID and a random token (e.g., `start_export`)
        self.unique_id = new_task_result_id(self.org.id)

    def _get(self, unique_id):
        return self.client.get(reverse("api:v3:cache_entries-detail", args=[unique_id]) + f"?organization_id={self.org.id}")

    def test_retrieve_own_task_result(self):
        set_task_result(self.unique_id, {"data": "exported"}, self.org.root.id, 60)

        response = self._get(self.unique_id)

        self.assertEqual(response.status_code, 200)
        # only the result itself is returned
        self.assertEqual(response.json(), {"data": "exported"})

    def test_retrieve_with_signed_organization_parameter(self):
        # the `organization` parameter is not cast to an integer by `get_org_id`, but still identifies the organization
        set_task_result(self.unique_id, {"data": "exported"}, self.org.root.id, 60)

        response = self.client.get(reverse("api:v3:cache_entries-detail", args=[self.unique_id]) + f"?organization=%2B{self.org.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": "exported"})

    def test_superuser_retrieves_task_result_of_any_org(self):
        # `has_perm` lets superusers access organizations they are not members of
        superuser_details = {"username": "superuser@demo.com", "password": "test_pass", "email": "superuser@demo.com"}
        User.objects.create_superuser(**superuser_details)
        self.client.login(**superuser_details)
        set_task_result(self.unique_id, {"data": "exported"}, self.org.root.id, 60)

        response = self._get(self.unique_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"data": "exported"})

    def test_retrieve_other_cache_entries_is_denied(self):
        other_org_unique_id = new_task_result_id(self.other_org.id)
        set_task_result(other_org_unique_id, {"data": "other org export"}, self.other_org.root.id, 60)
        set_cache_raw(f"access_token_{self.other_org.id}", {"token": "secret"})
        # e.g., a result keyed by the guessable ID (the organization ID and a 5-digit number) used before
        set_task_result(f"{self.org.id}12345", {"data": "exported"}, self.org.root.id, 60)

        for unique_id in (other_org_unique_id, f"access_token_{self.other_org.id}", f"{self.org.id}12345"):
            response = self._get(unique_id)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), NOT_FOUND)

    def test_retrieve_result_without_access_level_instance_is_denied(self):
        # e.g., a result cached before results were limited to access level instances, or by another writer
        for set_result in (
            lambda: set_cache_raw(self.unique_id, {"data": "exported"}),
            lambda: set_task_result(self.unique_id, {"data": "exported"}, None, 60),
            # nested-set bounds overlap between organizations, so another organization's root must not match
            lambda: set_task_result(self.unique_id, {"data": "exported"}, self.other_org.root.id, 60),
        ):
            set_result()
            response = self._get(self.unique_id)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), NOT_FOUND)

    def test_task_result_ids(self):
        unique_id = new_task_result_id(self.org.id)
        # random, so that they cannot be guessed or match another task's
        self.assertRegex(unique_id, rf"^{self.org.id}-[0-9a-f]{{32}}$")
        self.assertNotEqual(unique_id, new_task_result_id(self.org.id))
        self.assertTrue(is_task_result_id(unique_id, self.org.id))
        # only the organization's IDs, e.g., not another organization's whose ID starts with this one's
        token = unique_id.split("-")[1]
        for other_id in (f"{self.org.id}1-{token}", f"{self.org.id}12345", f"{self.org.id}-{token[:-1]}", f"{self.org.id}-{token.upper()}"):
            self.assertFalse(is_task_result_id(other_id, self.org.id), other_id)


class CacheEntryAccessLevelTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        self.sibling_member_user_details = {"username": "sibling_member@demo.com", "password": "test_pass"}
        self.sibling_member_user = User.objects.create_user(**self.sibling_member_user_details)
        self.org.add_member(self.sibling_member_user, self.sibling_level_instance.pk, ROLE_MEMBER)
        self.root_viewer_user_details = {"username": "root_viewer@demo.com", "password": "test_pass"}
        self.root_viewer_user = User.objects.create_user(**self.root_viewer_user_details)
        self.org.add_member(self.root_viewer_user, self.org.root.id, ROLE_VIEWER)

        self.cycle = self.cycle_factory.get_cycle()
        for ali in (self.root_level_instance, self.child_level_instance, self.sibling_level_instance):
            self.property_view_factory.get_property_view(prprty=self.property_factory.get_property(access_level_instance=ali))
        self.columns = [Column.objects.get(organization=self.org, table_name="PropertyState", column_name="address_line_1").column_name]

    def _login(self, user_details):
        self.client.logout()
        self.client.login(**user_details)

    def _start_export(self, user_details):
        self._login(user_details)
        url = reverse("api:v3:tax_lot_properties-start-export") + f"?organization_id={self.org.id}&inventory_type=properties"
        response = self.client.post(url, data=json.dumps({"columns": self.columns, "export_type": "csv"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        return response.json()["unique_id"]

    def _get(self, user_details, unique_id):
        self._login(user_details)
        return self.client.get(reverse("api:v3:cache_entries-detail", args=[unique_id]) + f"?organization_id={self.org.id}")

    def test_root_export_is_denied_to_child_and_sibling_members(self):
        unique_id = self._start_export(self.root_member_user_details)

        # the export has a header and the root, child, and sibling properties
        for user_details in (self.root_member_user_details, self.root_owner_user_details, self.superuser_details):
            response = self._get(user_details, unique_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["data"].strip().split("\n")), 4)

        for user_details in (self.child_member_user_details, self.sibling_member_user_details):
            response = self._get(user_details, unique_id)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), NOT_FOUND)

    def test_child_export_is_available_to_ancestors_only(self):
        unique_id = self._start_export(self.child_member_user_details)

        # the export has a header and the child property
        for user_details in (self.child_member_user_details, self.root_member_user_details):
            response = self._get(user_details, unique_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["data"].strip().split("\n")), 2)

        response = self._get(self.sibling_member_user_details, unique_id)
        self.assertEqual(response.status_code, 404)

    def test_export_started_with_signed_organization_parameter_can_be_retrieved(self):
        # the `organization` parameter is not cast to an integer by `get_org_id`, but the `unique_id` is prefixed by one
        self._login(self.root_member_user_details)
        url = reverse("api:v3:tax_lot_properties-start-export") + f"?organization=%2B{self.org.id}&inventory_type=properties"
        response = self.client.post(url, data=json.dumps({"columns": self.columns, "export_type": "csv"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        unique_id = str(response.json()["unique_id"])
        self.assertTrue(is_task_result_id(unique_id, self.org.id))

        response = self._get(self.root_member_user_details, unique_id)
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    def test_viewer_is_denied(self):
        unique_id = self._start_export(self.root_member_user_details)

        response = self._get(self.root_viewer_user_details, unique_id)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("data", response.json())
