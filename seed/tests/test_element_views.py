"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse
from rest_framework import status

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakeElementFactory, FakePropertyFactory
from seed.tests.util import AccessLevelBaseTestCase, AssertDictSubsetMixin, DeleteModelsTestCase
from seed.utils.organizations import create_organization


class ElementViewTests(AssertDictSubsetMixin, DeleteModelsTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.reverse = lambda viewname, args=None: f"{reverse(viewname, args=args)}?organization_id={self.org.pk}"

        # Fake Factories
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.element_factory = FakeElementFactory(organization=self.org)

        self.client.login(**user_details)

        # create properties with some elements
        self.property1 = self.property_factory.get_property(organization=self.org)
        self.property2 = self.property_factory.get_property(organization=self.org)
        self.element1 = self.element_factory.get_element(property=self.property1, installation_date="2024-01-01")
        self.element2 = self.element_factory.get_element(property=self.property1, installation_date="2024-01-03")
        self.element3 = self.element_factory.get_element(property=self.property1, installation_date="2024-01-02")

    def test_get_org_elements(self):
        url = self.reverse("api:v3:elements-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()
        data, total = results["results"], results["total"]
        self.assertEqual(total, 3)

        # Verify that elements are sorted by newest installation_date
        self.assertEqual(data[0]["installation_date"], "2024-01-03")
        self.assertEqual(data[1]["installation_date"], "2024-01-02")
        self.assertEqual(data[2]["installation_date"], "2024-01-01")

    def test_get_org_element(self):
        url = self.reverse("api:v3:elements-detail", args=[self.element3.element_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.element3.element_id)

    def test_get_property_elements(self):
        url = self.reverse("api:v3:property-elements-list", args=[self.property1.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 3)

        # Verify that elements are sorted by newest installation_date
        self.assertEqual(data[0]["installation_date"], "2024-01-03")
        self.assertEqual(data[1]["installation_date"], "2024-01-02")
        self.assertEqual(data[2]["installation_date"], "2024-01-01")

    def test_get_property_element(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property1.pk, self.element3.element_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.element3.element_id)

    def test_create_property_element(self):
        url = self.reverse("api:v3:property-elements-list", args=[self.property2.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 0)

        payload = {
            "id": "dcc29e47-814e-49c3-a3e1-02a0d3ab1abc",
            "code": "D304008",
            "description": "Mechanical Room AHU",
            "installation_date": "2004-06-01",
            "condition_index": 99.9827,
            "remaining_service_life": 14.416838,
            "replacement_cost": 233730,
            "extra_data": {
                "FLOWRATE": "15000",
                "FLOWRATE_UNITS": "cfm",
                "Quantity": 1,
                "Construction Type": "Permanent",
                "Operational Status": "Active",
            },
        }
        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        # Check that the element was attached to the property
        self.assertDictContainsSubset(payload, data)

        elements = self.property2.elements.all().values()
        self.assertEqual(1, len(elements))
        element = elements[0]
        self.assertEqual(data["id"], element["element_id"])

        response = self.client.post(
            url,
            {**payload, "id": "dcc29e47-814e-49c3-a3e1-02a0d3ab1abd", "extra_data": {"nested": {"key": "value"}}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"extra_data": ["Nested structures are not allowed"]})

    def test_update_property_element(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property1.pk, self.element1.element_id])

        response = self.client.get(url)
        element = response.json()

        payload = {}
        response = self.client.put(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"id": ["This field is required."], "code": ["This field is required."]})

        # Ignore created/modified fields when updating
        payload = {k: v for k, v in element.items() if k not in ["created", "modified"]}

        # Annual element condition update
        payload["condition_index"] = payload["condition_index"] * 0.8
        payload["remaining_service_life"] = payload["remaining_service_life"] - 1

        response = self.client.put(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(payload, response.json())

    def test_delete_property_element(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property1.pk, self.element1.element_id])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # element should return nothing now
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PropertyElementViewPermissionsTests(AccessLevelBaseTestCase, AssertDictSubsetMixin, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()
        self.reverse = lambda viewname, args=None: f"{reverse(viewname, args=args)}?organization_id={self.org.pk}"

        self.payload_data = {
            "id": "dcc29e47-814e-49c3-a3e1-02a0d3ab1abc",
            "code": "D304008",
            "description": "Mechanical Room AHU",
            "installation_date": "2004-06-01",
            "condition_index": 99.9827,
            "remaining_service_life": 14.416838,
            "replacement_cost": 233730,
            "extra_data": {
                "FLOWRATE": "15000",
                "FLOWRATE_UNITS": "cfm",
                "Quantity": 1,
                "Construction Type": "Permanent",
                "Operational Status": "Active",
            },
        }

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.element_factory = FakeElementFactory(organization=self.org)

        self.property = self.property_factory.get_property(organization=self.org)
        self.element = self.element_factory.get_element(property=self.property, installation_date="2024-01-01")

    def test_get_org_elements_permissions(self):
        url = self.reverse("api:v3:elements-list")

        self.login_as_child_member()
        response = self.client.get(url)
        assert response.json()["total"] == 0

        # root member can see all elements
        self.login_as_root_member()
        response = self.client.get(url)
        assert response.json()["total"] == 1

    def test_get_org_element_permissions(self):
        url = self.reverse("api:v3:elements-detail", args=[self.element.element_id])

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.get(url)
        assert response.status_code == 404
        assert response.json() == {"detail": "No Element matches the given query."}

        # root user can see element
        self.login_as_root_member()
        response = self.client.get(url)
        assert response.status_code == 200
        assert self.element.element_id == response.json()["id"]

    def test_get_property_elements_permissions(self):
        url = self.reverse("api:v3:property-elements-list", args=[self.property.pk])

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.get(url)
        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "No such resource."}

        # root user can see elements
        self.login_as_root_member()
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert self.element.element_id == data[0]["id"]

    def test_get_property_element_permissions(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property.pk, self.element.element_id])

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.get(url)
        assert response.status_code == 404
        assert response.json() == {"status": "error", "message": "No such resource."}

        # root user can see elements
        self.login_as_root_member()
        response = self.client.get(url)
        assert response.status_code == 200
        assert self.element.element_id == response.json()["id"]

    def test_create_property_element_permissions(self):
        url = self.reverse("api:v3:property-elements-list", args=[self.property.pk])

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.post(url, self.payload_data, content_type="application/json")
        assert response.status_code == 404

        # root user can create elements for all properties
        self.login_as_root_member()
        response = self.client.post(url, self.payload_data, content_type="application/json")
        assert response.status_code == 201

    def test_update_property_element_permissions(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property.pk, self.element.element_id])

        # Ignore created/modified fields when updating
        response = self.client.get(url)
        element = response.json()
        payload = {k: v for k, v in element.items() if k not in ["created", "modified"]}
        payload["condition_index"] = payload["condition_index"] * 0.8
        payload["remaining_service_life"] = payload["remaining_service_life"] - 1

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.put(url, payload, content_type="application/json")
        assert response.status_code == 404

        # root users can update elements
        self.login_as_root_member()
        response = self.client.put(url, payload, content_type="application/json")
        assert response.status_code == 200

    def test_delete_property_element_permissions(self):
        url = self.reverse("api:v3:property-elements-detail", args=[self.property.pk, self.element.element_id])

        # child user cannot tell that property exists
        self.login_as_child_member()
        response = self.client.delete(url)
        assert response.status_code == 404

        # root users can delete elements
        self.login_as_root_owner()
        response = self.client.delete(url)
        assert response.status_code == 204
