# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class TestPostOffice(TestCase):
    def setUp(self):
        self.fake_user = User.objects.create(username='test')
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
            from_email='me@me.com',
        )

        self.success_code = {
            self.client.get: 200,
            self.client.post: 201,
            self.client.delete: 204,
            self.client.put: 200,
            self.client.patch: 200,
        }

    def _test_permissions(self, client_method, url, params={}):
        # root owner user can
        self.login_as_root_owner()
        response = client_method(url, params, content_type='application/json')
        assert self.success_code[client_method]

        # root member user cannot
        self.login_as_root_member()
        response = client_method(url, params, content_type='application/json')
        assert response.status_code == 403

    def test_postoffice_email_list(self):
        url = reverse('api:v3:postoffice_email-list') + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_email_create(self):
        url = reverse('api:v3:postoffice_email-list') + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.post, url)

    def test_postoffice_email_retrieve(self):
        url = reverse('api:v3:postoffice_email-detail', args=[self.postoffice_email.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_email_put(self):
        url = reverse('api:v3:postoffice_email-detail', args=[self.postoffice_email.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.put, url)

    def test_postoffice_email_patch(self):
        url = reverse('api:v3:postoffice_email-detail', args=[self.postoffice_email.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.patch, url)

    def test_postoffice_email_destroy(self):
        url = reverse('api:v3:postoffice_email-detail', args=[self.postoffice_email.id]) + '?organization_id=' + str(self.org.id)
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
            self.client.patch: 200,
        }

    def _test_permissions(self, client_method, url, params={}):
        # root owner user can
        self.login_as_root_owner()
        response = client_method(url, params, content_type='application/json')
        assert self.success_code[client_method]

        # root member user cannot
        self.login_as_root_member()
        response = client_method(url, params, content_type='application/json')
        assert response.status_code == 403

    def test_postoffice_list(self):
        url = reverse('api:v3:postoffice-list') + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_create(self):
        url = reverse('api:v3:postoffice-list') + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.post, url)

    def test_postoffice_retrieve(self):
        url = reverse('api:v3:postoffice-detail', args=[self.postoffice.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.get, url)

    def test_postoffice_put(self):
        url = reverse('api:v3:postoffice-detail', args=[self.postoffice.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.put, url)

    def test_postoffice_patch(self):
        url = reverse('api:v3:postoffice-detail', args=[self.postoffice.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.patch, url)

    def test_postoffice_destroy(self):
        url = reverse('api:v3:postoffice-detail', args=[self.postoffice.id]) + '?organization_id=' + str(self.org.id)
        self._test_permissions(self.client.delete, url)
