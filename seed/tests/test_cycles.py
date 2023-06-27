# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

import pytz
from django.urls import reverse_lazy

from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase


class TestCycleViewSetPermissions(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()
        self.cycle = self.cycle_factory.get_cycle(organization=self.org)

    def test_cycle_create_permissions(self):
        url = reverse_lazy('api:v3:cycles-list') + "?organization_id=" + str(self.org.id)
        payload = {"name": "boo", "start": datetime.now(tz=pytz.UTC).isoformat(), "end": datetime.now(tz=pytz.UTC).isoformat()}

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 403

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 201

    def test_cycle_delete_permissions(self):
        url = reverse_lazy('api:v3:cycles-detail', args=[self.cycle.id]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users cannot
        self.login_as_root_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403

        # root users cannot
        self.login_as_root_owner()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 200

    def test_cycle_update_permissions(self):
        url = reverse_lazy('api:v3:cycles-detail', args=[self.cycle.id]) + "?organization_id=" + str(self.org.id)
        payload = {"name": "ah", "start": datetime.now(tz=pytz.UTC).isoformat(), "end": datetime.now(tz=pytz.UTC).isoformat()}

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 403

        # root users can see meters in root
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(payload), content_type='application/json')
        assert response.status_code == 200
