"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.urls import reverse_lazy

from seed.models import Property
from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase
from seed.utils.organizations import create_organization


class GBRPropertiesViewPermissionsTests(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()
        self.root_property = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)

    def test_gbr_properties_list(self):
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(self.org.id)

        # child user can
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 1

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 2

    def test_gbr_properties_list_excludes_other_organizations(self):
        # the other org's root shares the nested-set bounds of this org's root
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        self.property_factory.get_property(organization=other_org, access_level_instance=other_org.root)
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(self.org.id)

        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["pagination"]["total"] == 2
        assert {p["id"] for p in response.json()["properties"]} == {self.root_property.id, self.child_property.id}

    def test_gbr_properties_get(self):
        url = reverse_lazy("api:v3:gbr_properties-detail", args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

    def test_gbr_properties_destroy(self):
        url = reverse_lazy("api:v3:gbr_properties-detail", args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_gbr_properties_create(self):
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps({"access_level_instance_id": self.child_level_instance.id})

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

        params = json.dumps({"access_level_instance_id": self.root_level_instance.id})
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 403

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

    def test_gbr_properties_create_ignores_body_organization(self):
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(self.org.id)
        params = json.dumps({"access_level_instance_id": self.root_level_instance.id, "organization_id": other_org.id})

        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201
        assert Property.objects.get(pk=response.json()["message"]["id"]).organization_id == self.org.id
        assert not Property.objects.filter(organization=other_org).exists()

    def test_gbr_properties_create_defaults_to_root_access_level_instance(self):
        # an org with only a root access level instance doesn't require access_level_instance_id
        other_org, _, _ = create_organization(self.root_owner_user, "test-organization-b")
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(other_org.id)

        self.login_as_root_owner()
        response = self.client.post(url, json.dumps({}), content_type="application/json")
        assert response.status_code == 201
        created = Property.objects.get(pk=response.json()["message"]["id"])
        assert created.organization_id == other_org.id
        assert created.access_level_instance_id == other_org.root.id

    def test_gbr_properties_put(self):
        url = reverse_lazy("api:v3:gbr_properties-detail", args=[self.root_property.pk]) + "?organization_id=" + str(self.org.id)
        params = json.dumps({})

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 404

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.put(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_gbr_properties_create_rejects_unknown_access_level_instance(self):
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        url = reverse_lazy("api:v3:gbr_properties-list") + "?organization_id=" + str(self.org.id)
        count = Property.objects.count()

        # another org's, nonexistent, or malformed access level instances are rejected instead of erroring
        self.login_as_root_member()
        for access_level_instance_id in [other_org.root.id, -1, "abc"]:
            params = json.dumps({"access_level_instance_id": access_level_instance_id})
            response = self.client.post(url, params, content_type="application/json")
            assert response.status_code == 403
        assert Property.objects.count() == count

        params = json.dumps({"access_level_instance_id": self.child_level_instance.id})
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 201

    def test_gbr_properties_put_rejects_other_organization_parent_property(self):
        other_org, _, _ = create_organization(self.superuser, "test-organization-b")
        other_property = self.property_factory.get_property(organization=other_org, access_level_instance=other_org.root)
        url = reverse_lazy("api:v3:gbr_properties-detail", args=[self.child_property.pk]) + "?organization_id=" + str(self.org.id)

        self.login_as_root_member()
        response = self.client.put(url, json.dumps({"parent_property": other_property.pk}), content_type="application/json")
        assert response.status_code == 400
        self.child_property.refresh_from_db()
        assert self.child_property.parent_property_id is None

        response = self.client.put(url, json.dumps({"parent_property": self.root_property.pk}), content_type="application/json")
        assert response.status_code == 200
        self.child_property.refresh_from_db()
        assert self.child_property.parent_property_id == self.root_property.pk
