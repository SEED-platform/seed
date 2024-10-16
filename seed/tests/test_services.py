import json

from django.urls import reverse_lazy

from seed.models import Service
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
        assert response.json() == {'non_field_errors': ['Service name must be unique']}

        # group/system mismatch
        service_details["name"] = "new service 123"
        url = reverse_lazy("api:v3:system-services-list", args=[self.group1.id, self.system21.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(service_details), content_type="application/json")
        assert response.status_code == 400 
        assert response.json() == {'non_field_errors': ['No such resource.']}

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
        assert response.json() == {'detail': 'Not found.'}

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
        assert response.json()['results'] == []

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
        assert response.json() == {'detail': 'Not found.'}

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
        assert response.json() == {'detail': 'Not found.'}