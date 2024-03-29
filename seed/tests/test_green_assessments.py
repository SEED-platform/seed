# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nrel.gov
"""

import json

from django.urls import reverse_lazy

from seed.models import GreenAssessment, GreenAssessmentProperty, GreenAssessmentURL
from seed.tests.util import AccessLevelBaseTestCase


class TestGreenAssessmentsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)

    def test_green_assessments_list(self):
        url = reverse_lazy('api:v3:green_assessments-list') + '?organization_id=' + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_get(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + '?organization_id=' + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_destroy(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + '?organization_id=' + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_green_assessments_put(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + '?organization_id=' + str(self.org.id)
        params = json.dumps({'name': 'boo', 'recognition_type': 'AWD', 'is_numeric_score': True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_patch(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + '?organization_id=' + str(self.org.id)
        params = json.dumps({'name': 'boo', 'recognition_type': 'AWD', 'is_numeric_score': True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 200


class TestGreenAssessmentUrlsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.view = self.property_view_factory.get_property_view()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)
        self.property_assessment = GreenAssessmentProperty.objects.create(assessment=self.green_assessment, view=self.view)
        self.green_assessment_url = GreenAssessmentURL.objects.create(property_assessment=self.property_assessment)

    def test_green_assessment_urls_list(self):
        url = reverse_lazy('api:v3:green_assessment_urls-list') + '?organization_id=' + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_urls_get(self):
        url = (
            reverse_lazy('api:v3:green_assessment_urls-detail', args=[self.green_assessment_url.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_urls_destroy(self):
        url = (
            reverse_lazy('api:v3:green_assessment_urls-detail', args=[self.green_assessment_url.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_green_assessment_urls_put(self):
        url = (
            reverse_lazy('api:v3:green_assessment_urls-detail', args=[self.green_assessment_url.pk])
            + '?organization_id='
            + str(self.org.id)
        )
        params = json.dumps({'url': 'http://whatever.com', 'property_assessment': self.property_assessment.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_urls_patch(self):
        url = (
            reverse_lazy('api:v3:green_assessment_urls-detail', args=[self.green_assessment_url.pk])
            + '?organization_id='
            + str(self.org.id)
        )
        params = json.dumps({'url': 'http://whatever.com', 'property_assessment': self.property_assessment.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 200


class TestGreenAssessmentPropertiesPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.view = self.property_view_factory.get_property_view()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)
        self.property_assessment = GreenAssessmentProperty.objects.create(assessment=self.green_assessment, view=self.view)
        self.green_assessment_url = GreenAssessmentURL.objects.create(property_assessment=self.property_assessment)

    def test_green_assessment_properties_list(self):
        url = reverse_lazy('api:v3:green_assessment_properties-list') + '?organization_id=' + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_properties_get(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-detail', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_properties_bedes_format(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-bedes-format', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_properties_reso_format(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-reso-format', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_properties_destroy(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-detail', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_green_assessment_properties_put(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-detail', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )
        params = json.dumps({'assessment': self.green_assessment.pk, 'view': self.view.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessment_properties_patch(self):
        url = (
            reverse_lazy('api:v3:green_assessment_properties-detail', args=[self.property_assessment.pk])
            + '?organization_id='
            + str(self.org.id)
        )
        params = json.dumps({'assessment': self.green_assessment.pk, 'view': self.view.pk})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 200
