import json
from django.urls import reverse_lazy

from seed.test_helpers.fake import FakeInventoryGroupFactory, FakeSystemFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.models import System
from seed.serializers.systems import SystemSerializer


class SystemViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.group_factory = FakeInventoryGroupFactory(organization=self.org)
        self.system_factory = FakeSystemFactory(organization=self.org)

        self.group1 = self.group_factory.get_inventory_group()
        self.group2 = self.group_factory.get_inventory_group()

        # create systems for group1 and group2
        self.des1 = self.system_factory.get_system(group=self.group1, system_type="DES")
        self.des1 = self.system_factory.get_system(group=self.group1, system_type="DES")
        self.des3 = self.system_factory.get_system(group=self.group2)
        self.evse1 = self.system_factory.get_system(group=self.group1, system_type="EVSE")
        self.evse2 = self.system_factory.get_system(group=self.group1, system_type="EVSE")
        self.evse3 = self.system_factory.get_system(group=self.group2, system_type="EVSE")
        self.battery1 = self.system_factory.get_system(group=self.group1, system_type="Battery")
        self.battery2 = self.system_factory.get_system(group=self.group1, system_type="Battery")
        self.battery3 = self.system_factory.get_system(group=self.group2, system_type="Battery")

    def test_systems_by_type(self):
        url = reverse_lazy("api:v3:inventory_group-systems-systems-by-type", args=[self.group1.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert list(data.keys()) == ["DES", "EVSE", "Battery"]
        assert len(data["DES"]) == 2
        assert len(data["EVSE"]) == 2
        assert len(data["Battery"]) == 2

    def test_delete_system(self):
        system = self.system_factory.get_system(group=self.group1)

        assert System.objects.count() == 10
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, system.id]) + f"?organization_id={self.org.id}"
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204        
        assert System.objects.count() == 9

    def test_update_system(self):
        system = self.system_factory.get_system(group=self.group1, name="name 1", system_type="DES", count=10)

        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, system.id]) + f"?organization_id={self.org.id}"
        data = SystemSerializer(system).data
        data['name'] = "name 2"
        data['type'] = "DES"

        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        data = response.json()

        breakpoint()
        assert data["name"]


        assert True

