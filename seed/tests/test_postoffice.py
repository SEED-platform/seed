"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase
from django.urls import reverse
from post_office.models import Email

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestPostOffice(TestCase):
    def setUp(self):
        self.fake_user = User.objects.create(username="test")
        self.fake_org, _, _ = create_organization(self.fake_user)

    def test_default_template(self):
        template = PostOfficeEmailTemplate.objects.create()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 1)

        template.delete()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 0)


class TestPostOfficeEmailPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.postoffice_email = PostOfficeEmail.objects.create(
            organization=self.org,
            user=self.root_owner_user,
            from_email="me@me.com",
        )

        self.success_code = {
            self.client.get: 200,
            self.client.post: 201,
            self.client.delete: 204,
            self.client.put: 200,
            self.client.patch: 200,
        }

    def _test_permissions(self, client_method, url, params=None):
        # root owner user can
        if params is None:
            params = {}
        self.login_as_root_owner()
        response = client_method(url, params, content_type="application/json")
        assert self.success_code[client_method]

        # root member user cannot
        self.login_as_root_member()
        response = client_method(url, params, content_type="application/json")
        assert response.status_code == 403

    def test_postoffice_email_list(self):
        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_email_create(self):
        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.post, url)

    def test_postoffice_email_retrieve(self):
        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_email_put(self):
        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.put, url)

    def test_postoffice_email_patch(self):
        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.patch, url)

    def test_postoffice_email_destroy(self):
        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.delete, url)

    def test_postoffice_email_is_scoped_to_org(self):
        other_org = Organization.objects.create(name="other org")
        other_email = PostOfficeEmail.objects.create(organization=other_org, from_email="other@example.com")
        self.login_as_root_owner()

        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.org.id)
        response = self.client.get(url)
        assert response.status_code == 200
        assert [email["id"] for email in response.json()["data"]] == [self.postoffice_email.id]

        # another organization's emails cannot be retrieved, changed, or deleted
        url = reverse("api:v3:postoffice_email-detail", args=[other_email.id]) + "?organization_id=" + str(self.org.id)
        assert self.client.get(url).status_code == 404
        assert self.client.patch(url, {"subject": "changed"}, content_type="application/json").status_code == 404
        assert self.client.delete(url).status_code == 404
        other_email.refresh_from_db()
        assert other_email.subject != "changed"

        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        assert self.client.get(url).status_code == 200

    def test_postoffice_email_create_records_each_email(self):
        template = PostOfficeEmailTemplate.objects.create(organization=self.org, name="template", subject="Hello", content="Hello")
        states = [
            self.property_view_factory.get_property_view(
                state=self.property_state_factory.get_property_state(owner_email=owner_email)
            ).state
            for owner_email in ["first_owner@example.com", "second_owner@example.com"]
        ]

        self.login_as_root_owner()
        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.org.id)
        data = {
            "from_email": "dummy@example.com",
            "template_id": template.id,
            "inventory_id": [state.id for state in states],
            "inventory_type": "properties",
        }
        response = self.client.post(url, data, content_type="application/json")
        assert response.status_code == 201

        # each owner's email keeps its own recipient, and each sent email is recorded
        recipients = sorted(address for email in Email.objects.all() for address in email.to)
        assert recipients == ["first_owner@example.com", "second_owner@example.com"]
        recorded = PostOfficeEmail.objects.filter(organization=self.org).exclude(pk=self.postoffice_email.pk)
        assert sorted(address for email in recorded for address in email.to) == recipients


class TestPostOfficePermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.postoffice = PostOfficeEmailTemplate.objects.create(
            organization=self.org,
            user=self.root_owner_user,
        )

        self.success_code = {
            self.client.get: 200,
            self.client.post: 201,
            self.client.delete: 204,
            self.client.put: 200,
            self.client.patch: 200,
        }

    def _test_permissions(self, client_method, url, params=None):
        # root owner user can
        if params is None:
            params = {}
        self.login_as_root_owner()
        response = client_method(url, params, content_type="application/json")
        assert self.success_code[client_method]

        # root member user cannot
        self.login_as_root_member()
        response = client_method(url, params, content_type="application/json")
        assert response.status_code == 403

    def test_postoffice_list(self):
        url = reverse("api:v3:postoffice-list") + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_create(self):
        url = reverse("api:v3:postoffice-list") + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.post, url)

    def test_postoffice_retrieve(self):
        url = reverse("api:v3:postoffice-detail", args=[self.postoffice.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_put(self):
        url = reverse("api:v3:postoffice-detail", args=[self.postoffice.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.put, url)

    def test_postoffice_patch(self):
        url = reverse("api:v3:postoffice-detail", args=[self.postoffice.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.patch, url)

    def test_postoffice_destroy(self):
        url = reverse("api:v3:postoffice-detail", args=[self.postoffice.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.delete, url)
