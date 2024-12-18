import json

from django.urls import reverse_lazy

from seed.models import System
from seed.serializers.systems import SystemSerializer
from seed.test_helpers.fake import FakeInventoryGroupFactory, FakeSystemFactory
from seed.tests.util import AccessLevelBaseTestCase


class SystemViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.group_factory = FakeInventoryGroupFactory(organization=self.org)
        self.system_factory = FakeSystemFactory(organization=self.org)

        self.group1 = self.group_factory.get_inventory_group()
        self.group2 = self.group_factory.get_inventory_group()

        # create systems for group1 and group2
        self.des1 = self.system_factory.get_system(group=self.group1, system_type="DES")
        self.des2 = self.system_factory.get_system(group=self.group1, system_type="DES")
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
        assert list(data.keys()) == ["Battery", "DES - Cooling", "EVSE"]
        assert len(data["DES - Cooling"]) == 2
        assert len(data["EVSE"]) == 2
        assert len(data["Battery"]) == 2

    def test_system_delete(self):
        system = self.system_factory.get_system(group=self.group1)
        assert System.objects.count() == 10

        # group/system mismatch
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group2.id, system.id]) + f"?organization_id={self.org.id}"
        response = self.client.delete(url, content_type="application/json")

        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "No such resource."}
        assert System.objects.count() == 10

        # valid
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, system.id]) + f"?organization_id={self.org.id}"
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert System.objects.count() == 9

    def test_system_create(self):
        assert System.objects.count() == 9
        # DES
        data = {
            "name": "des new",
            "group_id": self.group1.id,
            "des_type": "Chiller",
            "type": "DES",
            "cooling_capacity": 1,
            "count": 2,
        }
        url = reverse_lazy("api:v3:inventory_group-systems-list", args=[self.group1.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 201
        data = response.json()["data"]
        assert sorted(data.keys()) == [
            "cooling_capacity",
            "count",
            "des_type",
            "group_id",
            "heating_capacity",
            "id",
            "mode",
            "name",
            "services",
            "type",
        ]
        assert System.objects.count() == 10

        # name constraint
        url = reverse_lazy("api:v3:inventory_group-systems-list", args=[self.group1.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 400
        data = response.json()
        assert data["errors"] == {"non_field_errors": ["System name must be unique within group"]}

        # # EVSE
        data = {
            "name": "evse new",
            "group_id": self.group1.id,
            "evse_type": "Level1-120V",
            "type": "EVSE",
            "power": 1,
            "voltage": 2,
            "count": 3,
        }
        url = reverse_lazy("api:v3:inventory_group-systems-list", args=[self.group1.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        data = response.json()["data"]
        assert sorted(data.keys()) == ["count", "evse_type", "group_id", "id", "name", "power", "services", "type", "voltage"]
        assert System.objects.count() == 11

        # BATTERY
        data = {
            "name": "battery new",
            "group_id": self.group1.id,
            "type": "Battery",
            "efficiency": 1,
            "power_capacity": 2,
            "energy_capacity": 3,
            "voltage": 4,
        }
        url = reverse_lazy("api:v3:inventory_group-systems-list", args=[self.group1.id]) + f"?organization_id={self.org.id}"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        data = response.json()["data"]
        assert sorted(data.keys()) == [
            "efficiency",
            "energy_capacity",
            "group_id",
            "id",
            "name",
            "power_capacity",
            "services",
            "type",
            "voltage",
        ]
        assert System.objects.count() == 12

    def test_system_update(self):
        des = self.system_factory.get_system(group=self.group1, name="des 1", system_type="DES", cooling_capacity=1)
        evse = self.system_factory.get_system(group=self.group1, name="evse 1", system_type="EVSE", power=2)
        battery = self.system_factory.get_system(group=self.group1, name="battery 1", system_type="Battery", voltage=3)

        # DES
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, des.id]) + f"?organization_id={self.org.id}"
        data = SystemSerializer(des).data
        data["cooling_capacity"] = 101
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert sorted(data.keys()) == [
            "cooling_capacity",
            "count",
            "des_type",
            "group_id",
            "heating_capacity",
            "id",
            "mode",
            "name",
            "services",
            "type",
        ]
        assert data["cooling_capacity"] == 101

        # name constraint
        data = SystemSerializer(des).data
        data["name"] = self.des1.name
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")

        # invalid
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group2.id, des.id]) + f"?organization_id={self.org.id}"
        data = SystemSerializer(des).data
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "No such resource."}
        # EVSE
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, evse.id]) + f"?organization_id={self.org.id}"
        data = SystemSerializer(evse).data
        data["power"] = 102
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        data = response.json()
        assert sorted(data.keys()) == ["count", "evse_type", "group_id", "id", "name", "power", "services", "type", "voltage"]
        assert data["power"] == 102

        # BATTERY
        url = reverse_lazy("api:v3:inventory_group-systems-detail", args=[self.group1.id, battery.id]) + f"?organization_id={self.org.id}"
        data = SystemSerializer(battery).data
        data["voltage"] = 103
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        data = response.json()
        assert sorted(data.keys()) == [
            "efficiency",
            "energy_capacity",
            "group_id",
            "id",
            "name",
            "power_capacity",
            "services",
            "type",
            "voltage",
        ]
        assert data["voltage"] == 103
