# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import mock
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from seed.audit_template.audit_template import AuditTemplate
from seed.landing.models import SEEDUser as User
from seed.models import AuditTemplateConfig

from seed.utils.organizations import create_organization

class atcron(TestCase):
    def setUp(self):
        settings.AUDIT_TEMPLATE_HOST = 'https://staging.labworks.org'
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.save()
        self.at = AuditTemplate(self.org.id)
        self.client.login(**self.user_details)

        self.atc = AuditTemplateConfig.objects.create(
            organization=self.org, 
            update_at_day=0,
            update_at_hour=1,
            update_at_minute=2
        )

    def tearDown(self):
        AuditTemplateConfig.objects.all().delete()

    def test_audit_template_config_list(self):
        url = reverse('api:v3:audit_template_configs-list') + f'?organization_id={self.org.id}'
        response = self.client.get(url, content_type='application/json')

        assert response.status_code == 200
        data = response.json()['data']
        assert len(data) == 1 
        assert data[0]['organization'] == self.org.id
        assert data[0]['update_at_day'] == 0
        assert data[0]['update_at_hour'] == 1
        assert data[0]['update_at_minute'] == 2

    def test_audit_template_config_create(self):
        AuditTemplateConfig.objects.all().delete()

        url = reverse('api:v3:audit_template_configs-list') + f'?organization_id={self.org.id}'
        params = {
            'update_at_day': 6,
            'update_at_hour': 23,
            'update_at_minute': 59
        }
        response = self.client.post(url, params, content_type='application/json')

        assert response.status_code == 201 
        data = response.json()['data'] 
        assert data['organization'] == self.org.id
        assert data['update_at_day'] == 6
        assert data['update_at_hour'] == 23
        assert data['update_at_minute'] == 59

        # testing one to one relationship
        response = self.client.post(url, params, content_type='application/json')
        assert response.status_code == 400 
        assert response.json()['errors'] == {'organization': ['This field must be unique.']}


    def test_audit_template_config_update(self):

        # Invalid params
        url = reverse('api:v3:audit_template_configs-detail', args=[self.atc.id]) + f'?organization_id={self.org.id}'
        params = {
            'update_at_day': 10,
            'update_at_hour': 50,
            'update_at_minute': 100
        }
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 400
        errors = response.json()['errors']
        assert errors['update_at_day'] == ['Ensure this value is less than or equal to 6.']
        assert errors['update_at_hour'] == ['Ensure this value is less than or equal to 23.']
        assert errors['update_at_minute'] == ['Ensure this value is less than or equal to 59.']

        self.atc.refresh_from_db()
        assert self.atc.update_at_day == 0
        assert self.atc.update_at_hour == 1
        assert self.atc.update_at_minute == 2

        # valid params
        params = {
            'update_at_day': 5,
            'update_at_hour': 15,
            'update_at_minute': 50
        }
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200
        data = response.json()['data']
        assert data['update_at_day'] == 5 
        self.atc.refresh_from_db() 
        assert self.atc.update_at_day == data['update_at_day']
        assert self.atc.update_at_hour == data['update_at_hour']
        assert self.atc.update_at_minute == data['update_at_minute']

        # no changes detected 
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200 
        assert response.json()['message'] == 'No changes detected.'


    def test_audit_template_config_delete(self):
        assert AuditTemplateConfig.objects.count() == 1
        url = reverse('api:v3:audit_template_configs-detail', args=[self.atc.id]) + f'?organization_id={self.org.id}'
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204
        assert AuditTemplateConfig.objects.count() == 0
