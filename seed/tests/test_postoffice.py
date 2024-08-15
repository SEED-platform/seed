# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from unittest import mock

from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestPostOfficeEmailTemplate(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.fake_user = User.objects.create(username="test")
        self.fake_org, _, _ = create_organization(self.fake_user)
        postoffice_details = {
            "name": "n fake",
            "description": "d fake",
            "subject": "s fake",
            "content": "c fake",
            "html_content": "h fake",
            "language": "en",
            "organization_id": self.fake_org.id,
        }
        self.fake_postoffice = PostOfficeEmailTemplate.objects.create(**postoffice_details)
        self.login_as_root_owner()

    def test_default_template(self):
        template = PostOfficeEmailTemplate.objects.create()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 2)

        template.delete()
        self.assertEqual(PostOfficeEmailTemplate.objects.count(), 1)

    def has_org_and_user(self, data):
        return "organization" in data and "user" in data

    def test_postoffice_crud(self):
        original_count = PostOfficeEmailTemplate.objects.count()
        # create
        url = reverse("api:v3:postoffice-list") + "?organization_id=" + str(self.org.id)
        params = {"name": "n1", "description": "d1", "subject": "s1", "content": "c1", "html_content": "h1", "language": "en"}
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201
        assert PostOfficeEmailTemplate.objects.count() == original_count + 1
        data = response.json()["data"]
        postoffice_email_template_id = data["id"]
        self.has_org_and_user(data)

        # list
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1
        data = response.json().get("data")[0]
        assert self.has_org_and_user(data)
        assert PostOfficeEmailTemplate.objects.count() == original_count + 1

        # update
        url = reverse("api:v3:postoffice-detail", args=[postoffice_email_template_id]) + "?organization_id=" + str(self.org.id)
        params = {"name": "n2", "description": "d1", "subject": "s1", "content": "c1", "html_content": "h1", "language": "en"}
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert self.has_org_and_user(data)
        assert PostOfficeEmailTemplate.objects.count() == original_count + 1

        # get
        url = reverse("api:v3:postoffice-detail", args=[postoffice_email_template_id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, cocontent_type="application/json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == postoffice_email_template_id
        assert data["name"] == "n2"
        assert self.has_org_and_user(data)

        # delete
        response = self.client.delete(url, cocontent_type="application/json")
        assert response.status_code == 204
        assert PostOfficeEmailTemplate.objects.count() == original_count

    def test_postoffice_email_template_org_constraint(self):
        url = reverse("api:v3:postoffice-list") + "?organization_id=" + str(self.fake_org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        response = self.client.get(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.put(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.delete(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}


class TestPostOfficeEmail(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.cycle1 = self.cycle_factory.get_cycle()
        self.property1 = self.property_factory.get_property()
        self.state1 = self.property_state_factory.get_property_state()
        self.view1 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state1, cycle=self.cycle1)

        self.fake_user = User.objects.create(username="test")
        self.fake_org, _, _ = create_organization(self.fake_user)
        self.fake_postoffice_email = PostOfficeEmail.objects.create(
            organization=self.fake_org,
            user=self.fake_user,
            from_email="me@me.com",
        )
        postoffice_details = {
            "name": "n1",
            "description": "d1",
            "subject": "s1",
            "content": "c1",
            "html_content": "h1",
            "language": "en",
            "organization_id": self.org.id,
        }
        self.postoffice = PostOfficeEmailTemplate.objects.create(**postoffice_details)
        self.success_code = {
            self.client.get: 200,
            self.client.post: 201,
            self.client.delete: 204,
            self.client.put: 200,
        }
        self.login_as_root_owner()

    def has_org_and_user(self, data):
        return data["organization"] == self.org.id and data["user"] == self.root_owner_user.id

    @mock.patch("post_office.tasks.send_queued_mail.delay")
    def test_postoffice_email_crud(self, mock_send_mail):
        mock_send_mail.return_value = None
        original_count = PostOfficeEmail.objects.count()

        # create (invalid inventory_id)
        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.org.id)
        params = {
            "from_email": "a@a.com",
            "inventory_type": "properties",
            "inventory_id": self.state1.id,
            "template_id": self.postoffice.id,
        }

        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 400
        assert response.json() == {"status": "error", "message": {"non_field_errors": ["'inventory_id' must be a list."]}}

        # create (valid)
        params["inventory_id"] = [self.state1.id]
        response = self.client.post(url, params, content_type="application/json")
        data = response.json().get("data")
        postoffice_email_id = data["id"]
        assert response.status_code == 201
        assert PostOfficeEmail.objects.count() == original_count + 1
        assert self.has_org_and_user(data)

        # list
        response = self.client.get(url, content_type="application/json")
        data = response.json()["data"]
        assert response.status_code == 200
        assert len(data) == 1
        assert PostOfficeEmail.objects.count() == original_count + 1
        assert data[0]["id"] == postoffice_email_id
        assert self.has_org_and_user(data[0])

        # update
        url = reverse("api:v3:postoffice_email-detail", args=[postoffice_email_id]) + "?organization_id=" + str(self.org.id)
        params = {"from_email": "b@b.com", "template_id": self.postoffice.id}
        response = self.client.put(url, params, content_type="application/json")
        data = response.json().get("data")
        assert response.status_code == 200
        assert data["id"] == postoffice_email_id
        assert data["from_email"] == "b@b.com"
        assert self.has_org_and_user(data)

        # get
        response = self.client.get(url, content_type="application/json")
        data = response.json()["data"]
        assert response.status_code == 200
        assert data["id"] == postoffice_email_id
        assert data["from_email"] == "b@b.com"
        assert self.has_org_and_user(data)

        # delete
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert PostOfficeEmail.objects.count() == original_count

        # delete on wrong org
        url = reverse("api:v3:postoffice_email-detail", args=[self.fake_postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "Not found."}
        assert PostOfficeEmail.objects.filter(id=self.fake_postoffice_email.id).exists()
        assert PostOfficeEmail.objects.count() == original_count

    def test_postoffice_email_org_constraint(self):
        url = reverse("api:v3:postoffice_email-list") + "?organization_id=" + str(self.fake_org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        response = self.client.get(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice_email-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice_email-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.put(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}

        url = reverse("api:v3:postoffice_email-detail", args=[1]) + "?organization_id=" + str(self.fake_org.id)
        response = self.client.delete(url, {}, content_type="application/json")
        assert response.status_code == 403
        assert response.json() == {"status": "error", "message": "You do not have permission to perform this action."}


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
        }

    def _test_permissions(self, client_method, url, params={}):
        # root owner user can
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

    def test_postoffice_email_destroy(self):
        url = reverse("api:v3:postoffice_email-detail", args=[self.postoffice_email.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.delete, url)


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
        }

    def _test_permissions(self, client_method, url, params={}):
        # root owner user can
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

    def test_postoffice_destroy(self):
        url = reverse("api:v3:postoffice-detail", args=[self.postoffice.id]) + "?organization_id=" + str(self.org.id)
        self._test_permissions(self.client.delete, url)
