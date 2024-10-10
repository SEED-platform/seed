from django.urls import reverse_lazy

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
