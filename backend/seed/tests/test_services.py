"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.urls import reverse_lazy

from seed.lib.superperms.orgs.models import ROLE_MEMBER
from seed.models import InventoryGroupMapping, Meter, Service
from seed.test_helpers.fake import FakeInventoryGroupFactory, FakeServiceFactory, FakeSystemFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class ServiceViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.group_factory = FakeInventoryGroupFactory(organization=self.org)
        self.system_factory = FakeSystemFactory(organization=self.org)
        self.service_factory = FakeServiceFactory()

        self.group1 = self.group_factory.get_inventory_group()
        self.system11 = self.system_factory.get_system(group=self.group1)
        self.system12 = self.system_factory.get_system(group=self.group1)
        self.service111 = self.service_factory.get_service(system=self.system11, name="s111")
        self.service112 = self.service_factory.get_service(system=self.system11, name="s112")
        self.service121 = self.service_factory.get_service(system=self.system12, name="s121")
        # org2
        self.org2, _, _ = create_organization(self.superuser, "org2")
        self.group2 = self.group_factory.get_inventory_group(organization=self.org2, access_level_instance=self.org2.root)
        self.system21 = self.system_factory.get_system(group=self.group2)
        self.service211 = self.service_factory.get_service(system=self.system21, name="s211")

    def test_service_create(self):
        # valid
        assert Service.objects.count() == 4
        service_details = {"emission_factor": 10, "name": "new service", "system_id": self.system11.id}
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system11.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new service"
        assert Service.objects.count() == 5

        # duplicate name
        response = self.client.post(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 400
        assert response.json() == {"non_field_errors": ["Service name must be unique within system"]}

    def test_service_delete(self):
        # valid
        service = self.service_factory.get_service(system=self.system11)
        assert Service.objects.count() == 5
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, service.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert Service.objects.count() == 4

        # dne
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system21.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"detail": "No Service matches the given query."}

    def test_service_list(self):
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system11.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        data = response.json()["results"]
        assert len(data) == 2
        assert Service.objects.count() == 4

        # group/system mismatch
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system21.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_service_retrieve(self):
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == self.service111.id
        assert data["name"] == "s111"

        # dne
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system21.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "No Service matches the given query."}

    def test_service_update(self):
        service = self.service_factory.get_service(system=self.system11, name="original name", emission_factor=1)

        service_details = {"emission_factor": 10, "name": "new name", "system_id": self.system11.id}
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, service.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.put(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service.id
        assert data["name"] == "new name"
        assert data["emission_factor"] == 10

        # dne
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system21.id, service.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.put(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"detail": "No Service matches the given query."}

    def test_service_retrieve_other_organization(self):
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system21.id, self.service211.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404

    def test_service_create_uses_path_system(self):
        # the path's system must belong to the path's group
        service_details = {"name": "new service", "system_id": self.system21.id}
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system21.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 404
        assert not Service.objects.filter(name="new service").exists()

        # the body's system_id is ignored
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system11.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 201
        assert Service.objects.get(name="new service").system_id == self.system11.id

        # services can not be moved to another system
        url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.put(url, data=json.dumps({"name": "s111", "system_id": self.system21.id}), content_type="application/json")
        assert response.status_code == 200
        self.service111.refresh_from_db()
        assert self.service111.system_id == self.system11.id

    def test_service_permissions(self):
        list_url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system11.id]) + f"?organization_id={self.org.id}"
        detail_url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )
        service_details = {"emission_factor": 10, "name": "new service", "system_id": self.system11.id}

        # group1 is at the root, above the child member's access level
        self.login_as_child_member()
        assert self.client.get(list_url, content_type="application/json").status_code == 404
        assert self.client.post(list_url, data=json.dumps(service_details), content_type="application/json").status_code == 404
        assert self.client.put(detail_url, data=json.dumps(service_details), content_type="application/json").status_code == 404
        assert self.client.delete(detail_url, content_type="application/json").status_code == 404
        self.service111.refresh_from_db()
        assert self.service111.name == "s111"
        assert Service.objects.count() == 4

        # users of other organizations have no access
        self.org2.add_member(self.root_member_user, self.org2.root.id, ROLE_MEMBER)
        self.login_as_root_member()
        other_org_url = (
            reverse_lazy("api:v3:system-services-detail", args=[self.group1.id, self.system11.id, self.service111.id])
            + f"?organization_id={self.org2.id}"
        )
        assert self.client.delete(other_org_url, content_type="application/json").status_code == 404
        assert Service.objects.count() == 4

        # root members have access
        assert self.client.get(list_url, content_type="application/json").status_code == 200
        assert self.client.delete(detail_url, content_type="application/json").status_code == 204
        assert Service.objects.count() == 3

    def test_service_create_meters(self):
        view = self.property_view_factory.get_property_view()
        other_view = self.property_view_factory.get_property_view()
        InventoryGroupMapping.objects.create(property=view.property, group=self.group1)
        url = (
            reverse_lazy("api:v3:system-services-create-meters", args=[self.group1.id, self.system11.id, self.service111.id])
            + f"?organization_id={self.org.id}"
        )

        # missing args
        data = {"property_ids": [view.property_id], "type": "Electric"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 400
        assert Meter.objects.count() == 0

        # unknown meter type
        data = {"property_ids": [view.property_id], "direction": "imported", "type": "Unknown"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 400
        assert Meter.objects.count() == 0

        # properties must be in the group
        data = {"property_ids": [view.property_id, other_view.property_id], "direction": "imported", "type": "Electric"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 404
        assert Meter.objects.count() == 0

        # the service must be in the path's system
        other_service_url = (
            reverse_lazy("api:v3:system-services-create-meters", args=[self.group1.id, self.system11.id, self.service211.id])
            + f"?organization_id={self.org.id}"
        )
        data = {"property_ids": [view.property_id], "direction": "imported", "type": "Electric"}
        response = self.client.post(other_service_url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 404
        assert Meter.objects.count() == 0

        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        meter = Meter.objects.get()
        assert meter.property_id == view.property_id
        assert meter.service_id == self.service111.id
        assert meter.connection_type == Meter.RECEIVING_SERVICE
