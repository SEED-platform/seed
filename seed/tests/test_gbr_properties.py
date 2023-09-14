import json

from django.urls import reverse_lazy

from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase


class GBRPropertiesViewPermisionsTests(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()
        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)

    def test_gbr_properties_list(self):
        url = reverse_lazy('api:v3:gbr_properties-list') + "?organization_id=" + str(self.org.id)

        # child user can
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 1

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 2

    def test_gbr_properties_get(self):
        url = reverse_lazy('api:v3:gbr_properties-detail', args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200

    def test_gbr_properties_destroy(self):
        url = reverse_lazy('api:v3:gbr_properties-detail', args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204

    def test_gbr_properties_create(self):
        url = reverse_lazy('api:v3:gbr_properties-list') + "?organization_id=" + str(self.org.id)
        params = json.dumps({"access_level_instance_id": self.child_level_instance.id})

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type='application/json')
        assert response.status_code == 201

        params = json.dumps({"access_level_instance_id": self.root_level_instance.id})
        response = self.client.post(url, params, content_type='application/json')
        assert response.status_code == 403

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.post(url, params, content_type='application/json')
        assert response.status_code == 201

    def test_gbr_properties_put(self):
        url = reverse_lazy('api:v3:gbr_properties-detail', args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.put(url, params, content_type='application/json')
        assert response.status_code == 200
