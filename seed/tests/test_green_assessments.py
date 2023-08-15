
# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author nicholas.long@nrel.gov
"""
import json

from django.urls import reverse_lazy

from seed.models import GreenAssessment
from seed.tests.util import AccessLevelBaseTestCase


class TestGreenAssessmentsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.green_assessment = GreenAssessment.objects.create(organization_id=self.org.id, is_numeric_score=True)

    def test_green_assessments_list(self):
        url = reverse_lazy('api:v3:green_assessments-list') + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_get(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_destroy(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_green_assessments_put(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({"name": "boo", "recognition_type": "AWD", "is_numeric_score": True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200

    def test_green_assessments_patch(self):
        url = reverse_lazy('api:v3:green_assessments-detail', args=[self.green_assessment.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({"name": "boo", "recognition_type": "AWD", "is_numeric_score": True})

        # child user cannot
        self.login_as_child_member()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.patch(url, params, content_type='application/json')
        assert response.status_code == 200
