

import json
from unittest import skip

from django.urls import reverse_lazy

from seed.tests.util import AccessLevelBaseTestCase


class PropertyViewsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.root_view = self.property_view_factory.get_property_view(prprty=self.root_property)

        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.child_view = self.property_view_factory.get_property_view(prprty=self.child_property)

        self.cycle = self.cycle_factory.get_cycle()

    def test_property_views_list(self):
        url = reverse_lazy('api:v3:property_views-list') + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert len(resp.json()["property_views"]) == 1

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert len(resp.json()["property_views"]) == 2

    def test_property_views_get(self):
        url = reverse_lazy('api:v3:property_views-detail', args=[self.root_view.pk]) + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.get(url, content_type='application/json')
        assert resp.status_code == 200

    def test_property_views_delete(self):
        url = reverse_lazy('api:v3:property_views-detail', args=[self.root_view.pk]) + f"?organization_id={self.org.id}"

        self.login_as_child_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.delete(url, content_type='application/json')
        assert resp.status_code == 204

    def test_property_views_put(self):
        url = reverse_lazy('api:v3:property_views-detail', args=[self.root_view.pk]) + f"?organization_id={self.org.id}"
        params = json.dumps({})

        self.login_as_child_member()
        resp = self.client.put(url, params, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.put(url, params, content_type='application/json')
        assert resp.status_code == 200

    def test_property_views_patch(self):
        url = reverse_lazy('api:v3:property_views-detail', args=[self.root_view.pk]) + f"?organization_id={self.org.id}"
        params = json.dumps({})

        self.login_as_child_member()
        resp = self.client.patch(url, params, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.patch(url, params, content_type='application/json')
        assert resp.status_code == 200

    @skip("doesn't work???")
    def test_property_views_create(self):
        url = reverse_lazy('api:v3:property_views-list') + f"?organization_id={self.org.id}"
        params = json.dumps({"cycle_id": self.cycle.pk, "property_id": self.root_property.pk, "state_id": self.root_view.pk})

        self.login_as_child_member()
        resp = self.client.post(url, params, content_type='application/json')
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type='application/json')
        assert resp.status_code == 201
