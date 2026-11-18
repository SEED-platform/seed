"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER
from seed.models import OrganizationUser
from seed.test_helpers.fake import (
    FakeColumnListProfileFactory,
    FakeCycleFactory,
)
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class OrganizationUserViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.org_user = OrganizationUser.objects.get(organization=self.org, user=self.superuser)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.superuser)
        self.profile_factory = FakeColumnListProfileFactory(organization=self.org)

        self.cycle1 = self.cycle_factory.get_cycle()
        self.cycle2 = self.cycle_factory.get_cycle()

        self.profile1 = self.profile_factory.get_columnlistprofile()
        self.profile2 = self.profile_factory.get_columnlistprofile()

    def test_update_settings(self):
        # real filters and sorts will be appended with an id: "pm_property_id_123"
        filters = {"pm_property_id": {"filter": "1", "filterType": "text", "type": "contains"}}
        sorts = ["pm_property_id", "-custom_id_1"]
        data = {"settings": {"cycle": self.cycle1.pk, "profile": self.profile2.pk, "sorts": sorts, "filters": filters}}
        url = reverse("api:v4:organization_users-detail", args=[self.org_user.pk]) + f"?organization_id={self.org.pk}"

        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(set(data.keys()), {"settings", "role_level", "status", "organization", "user", "email", "first_name", "last_name"})
        self.assertEqual(data["role_level"], 20)

        self.org_user.refresh_from_db()
        self.assertEqual(self.org_user.settings["cycle"], self.cycle1.pk)
        self.assertEqual(self.org_user.settings["profile"], self.profile2.pk)
        self.assertEqual(self.org_user.settings["sorts"], sorts)
        self.assertEqual(self.org_user.settings["filters"], filters)
        self.assertEqual(self.org_user.role_level, 20)

        # passing data without settings resets settings
        data = {"role_level": 10}
        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.org_user.refresh_from_db()
        self.assertEqual(self.org_user.settings, {})
        self.assertEqual(self.org_user.role_level, 10)

    def test_update_settings_is_limited_to_own_settings(self):
        owner_org_user = OrganizationUser.objects.get(organization=self.org, user=self.root_owner_user)
        member_org_user = OrganizationUser.objects.get(organization=self.org, user=self.root_member_user)
        owner_settings = owner_org_user.settings
        data = {"settings": {"cycle": self.cycle1.pk}, "role_level": ROLE_OWNER}
        self.login_as_root_member()

        # users cannot update other users
        url = reverse("api:v4:organization_users-detail", args=[owner_org_user.pk]) + f"?organization_id={self.org.pk}"
        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        owner_org_user.refresh_from_db()
        self.assertEqual(owner_org_user.settings, owner_settings)

        # users can update their own settings, but not their role
        url = reverse("api:v4:organization_users-detail", args=[member_org_user.pk]) + f"?organization_id={self.org.pk}"
        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["role_level"], ROLE_MEMBER)
        member_org_user.refresh_from_db()
        self.assertEqual(member_org_user.settings, {"cycle": self.cycle1.pk})
        self.assertEqual(member_org_user.role_level, ROLE_MEMBER)

    def test_viewer_cannot_escalate_role_or_change_organization(self):
        viewer_details = {"username": "root_viewer@demo.com", "password": "test_pass"}
        viewer = User.objects.create_user(**viewer_details)
        self.org.add_member(viewer, self.org.root.id, ROLE_VIEWER)
        viewer_org_user = OrganizationUser.objects.get(organization=self.org, user=viewer)
        other_org, _, _ = create_organization(self.superuser, "other-organization")
        self.client.login(**viewer_details)
        url = reverse("api:v4:organization_users-detail", args=[viewer_org_user.pk]) + f"?organization_id={self.org.pk}"

        for data in ({"role_level": ROLE_OWNER}, {"organization": other_org.pk, "role_level": ROLE_MEMBER}):
            response = self.client.put(url, data=data, content_type="application/json")
            self.assertEqual(response.status_code, 200)
            viewer_org_user.refresh_from_db()
            self.assertEqual(viewer_org_user.role_level, ROLE_VIEWER)
            self.assertEqual(viewer_org_user.organization_id, self.org.pk)
        self.assertFalse(OrganizationUser.objects.filter(organization=other_org, user=viewer).exists())

    def test_superuser_cannot_move_org_user_or_make_non_root_owner(self):
        other_org, _, _ = create_organization(self.superuser, "other-organization")
        child_org_user = OrganizationUser.objects.get(organization=self.org, user=self.child_member_user)
        url = reverse("api:v4:organization_users-detail", args=[child_org_user.pk]) + f"?organization_id={self.org.pk}"

        for data in ({"organization": other_org.pk}, {"role_level": ROLE_OWNER}):
            response = self.client.put(url, data=data, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            child_org_user.refresh_from_db()
            self.assertEqual(child_org_user.organization_id, self.org.pk)
            self.assertEqual(child_org_user.role_level, ROLE_MEMBER)
