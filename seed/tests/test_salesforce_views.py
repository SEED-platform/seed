"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.timezone import get_current_timezone

from config.settings.test import SF_DOMAIN, SF_INSTANCE, SF_PASSWORD, SF_SECURITY_TOKEN, SF_USERNAME
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER
from seed.models import Column, PropertyView, SalesforceConfig, SalesforceMapping
from seed.models import StatusLabel as Label
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.encrypt import encrypt
from seed.utils.organizations import create_organization
from seed.utils.salesforce import update_salesforce_property
from seed.views.v3.label_inventories import LabelInventoryViewSet


class SalesforceViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.api_view = LabelInventoryViewSet()
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.client.login(**user_details)

        # setup labels
        self.ind_label = Label.objects.create(name="Indication Label", super_organization=self.org)
        self.violation_label = Label.objects.create(name="Violation Label", super_organization=self.org)
        self.compliance_label = Label.objects.create(name="Compliance Label", super_organization=self.org)

        # setup some columns
        self.benchmark_col, _ = Column.objects.get_or_create(
            table_name="PropertyState",
            column_name="Salesforce Benchmark ID",
            organization=self.org,
            is_extra_data=True,
        )
        self.sqft_col, _ = Column.objects.get_or_create(
            table_name="PropertyState",
            column_name="Property GFA - Calculated (Buildings and Parking) (ft2)",
            organization=self.org,
            is_extra_data=True,
        )
        self.site_eui_col, _ = Column.objects.get_or_create(
            table_name="PropertyState",
            column_name="site_eui",
            organization=self.org,
            display_name="Site EUI",
            column_description="Site EUI",
            is_extra_data=False,
            data_type="eui",
        )

        self.sf_config = SalesforceConfig.objects.create(
            organization=self.org,
            compliance_label=self.compliance_label,
            indication_label=self.ind_label,
            violation_label=self.violation_label,
            seed_benchmark_id_column=self.benchmark_col,
            unique_benchmark_id_fieldname="Salesforce_Benchmark_ID__c",
            status_fieldname="Status__c",
        )

        # test saving salesforce mappings / CRUD
        self.mapping_sqft = SalesforceMapping.objects.create(
            salesforce_fieldname="Benchmark_Square_Footage__c",
            column=self.sqft_col,
            organization=self.org,
        )

        self.mapping_site_eui = SalesforceMapping.objects.create(
            salesforce_fieldname="Site_EUI_kBtu_ft2__c",
            column=self.site_eui_col,
            organization=self.org,
        )

    def test_update_at_hour_constraint(self):
        constraint_name = "salesforce_update_at_hour_range"
        self.sf_config.update_at_hour = 25
        with transaction.atomic(), self.assertRaisesMessage(IntegrityError, constraint_name):
            self.sf_config.save()

    def test_update_at_minute_constraint(self):
        constraint_name = "salesforce_update_at_minute_range"
        self.sf_config.update_at_minute = 62
        with transaction.atomic(), self.assertRaisesMessage(IntegrityError, constraint_name):
            self.sf_config.save()

    def test_save_salesforce_config(self):
        # use new org b/c can only have 1 config record on an org
        temp_org, _, _ = create_organization(self.user)

        ind_label = Label.objects.create(name="Indication Label", super_organization=temp_org)
        violation_label = Label.objects.create(name="Violation Label", super_organization=temp_org)
        compliance_label = Label.objects.create(name="Compliance Label", super_organization=temp_org)

        status_fieldname = "Status__Yay__c"

        payload_data = {
            "indication_label": ind_label.id,
            "violation_label": violation_label.id,
            "compliance_label": compliance_label.id,
            "unique_benchmark_id_fieldname": "Salesforce_Benchmark_ID__c",
            "status_fieldname": status_fieldname,
        }

        response = self.client.post(
            reverse("api:v3:salesforce_configs-list") + "?organization_id=" + str(temp_org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")

        tmp_sf_config = SalesforceConfig.objects.get(pk=data["salesforce_config"]["id"])
        self.assertTrue(isinstance(tmp_sf_config, SalesforceConfig))
        self.assertEqual(tmp_sf_config.status_fieldname, status_fieldname)

        # test editing salesforce configs
        tmp_contact_rec_type = "testing_editing"
        tmp_sf_config.contact_rec_type = tmp_contact_rec_type
        tmp_sf_config.save()

        self.assertEqual(tmp_sf_config.contact_rec_type, tmp_contact_rec_type)

    def test_save_salesforce_mapping(self):
        # test saving salesforce mappings

        self.energystar_col, _ = Column.objects.get_or_create(
            table_name="PropertyState", column_name="ENERGY STAR Score", organization=self.org, is_extra_data=True
        )

        # create new mapping
        payload_data = {"salesforce_fieldname": "ENERGY_STAR_Score__c", "column": self.site_eui_col.id}
        response = self.client.post(
            reverse("api:v3:salesforce_mappings-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")

        self.mapping_energystar = SalesforceMapping.objects.filter(salesforce_fieldname="ENERGY_STAR_Score__c").first()

        # Edit salesforce mappings
        new_data = {"salesforce_fieldname": "the_new_field__c"}
        url = reverse("api:v3:salesforce_mappings-detail", args=[self.mapping_energystar.pk]) + f"?organization_id={self.org.pk}"
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")

        mapping = SalesforceMapping.objects.get(pk=self.mapping_energystar.pk)
        self.assertEqual(mapping.salesforce_fieldname, new_data["salesforce_fieldname"])

        # TODO: use view to delete
        self.client.delete(url, content_type="application/json")

        # catch exception here
        with pytest.raises(SalesforceMapping.DoesNotExist):
            SalesforceMapping.objects.get(pk=self.mapping_energystar.pk)

    def test_salesforce_connection_fails(self):
        # test error when connection to salesforce fails due to no connection params

        self.org.salesforce_enabled = True
        self.org.save()

        payload_data = {"salesforce_config": {"instance": None, "username": None, "password": None, "security_token": None}}
        if SF_DOMAIN == "test":
            payload_data["salesforce_config"]["domain"] = SF_DOMAIN

        response = self.client.post(
            reverse("api:v3:salesforce_configs-salesforce-connection") + "?organization_id=" + str(self.org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)

        self.assertEqual(data["status"], "error")
        self.assertIn("Salesforce Authentication Failed:", data["message"])

    def test_salesforce_connection_success(self):
        # test salesforce connection

        # enable sf
        self.org.salesforce_enabled = True
        self.org.save()

        payload_data = {
            "salesforce_config": {
                "instance": SF_INSTANCE,
                "username": SF_USERNAME,
                "password": SF_PASSWORD,
                "security_token": SF_SECURITY_TOKEN,
            }
        }

        if SF_DOMAIN == "test":
            payload_data["salesforce_config"]["domain"] = SF_DOMAIN

        response = self.client.post(
            reverse("api:v3:salesforce_configs-salesforce-connection") + "?organization_id=" + str(self.org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)

        self.assertEqual(data["status"], "success")

    def test_pushing_salesforce_benchmark(self):
        state = self.property_state_factory.get_property_state()

        # this ID should be valid for the test salesforce sandbox
        state.extra_data["Salesforce Benchmark ID"] = "a01Ea00000VqqMf"
        # add other Instance specific mappings for testing
        state.extra_data["Property GFA - Calculated (Buildings and Parking) (ft2)"] = state.gross_floor_area
        state.save()

        property = self.property_factory.get_property()
        view = PropertyView.objects.create(property=property, cycle=self.cycle, state=state)

        self.api_view.add_labels(self.api_view.models["property"].objects.none(), "property", [view.id], [self.ind_label.id])
        self.api_view.add_labels(self.api_view.models["property"].objects.none(), "property", [view.id], [self.compliance_label.id])

        # pdata = PropertyViewSerializer(view).data
        # print(f" view data: {pdata}")

        # enable sf
        self.sf_config.url = SF_INSTANCE
        self.sf_config.username = SF_USERNAME
        self.sf_config.password = encrypt(SF_PASSWORD)
        self.sf_config.security_token = SF_SECURITY_TOKEN
        if SF_DOMAIN == "test":
            self.sf_config.domain = SF_DOMAIN
        self.sf_config.save()

        status, _message = update_salesforce_property(self.org.id, view.id)

        self.assertEqual(status, True)

    def test_multiple_salesforce_configs_illegal(self):
        """test that you can't have 2 salesforce_configs records per org
        (catch error)
        """

        # we already have a config saved to this org, try to save another
        with transaction.atomic(), pytest.raises(IntegrityError):
            SalesforceConfig.objects.create(
                organization=self.org,
                status_fieldname="Status__c",
            )

    def test_no_sync_when_disabled(self):
        """
        test that auto sync does not run when salesforce functionality is disabled
        """

        # disable sf
        self.org.salesforce_enabled = False
        self.org.save()

        response = self.client.post(
            reverse("api:v3:salesforce_configs-sync") + "?organization_id=" + str(self.org.id), data={}, content_type="application/json"
        )
        data = json.loads(response.content)

        self.assertEqual(data["status"], "error")
        self.assertIn("Salesforce Workflow is not enabled", data["message"][0])

    # TODO: test auto sync works and sets date


class SalesforceViewTestPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.api_view = LabelInventoryViewSet()
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.login_as_root_member()

        # setup labels
        self.ind_label = Label.objects.create(name="Indication Label", super_organization=self.org)
        self.violation_label = Label.objects.create(name="Violation Label", super_organization=self.org)
        self.compliance_label = Label.objects.create(name="Compliance Label", super_organization=self.org)

        # setup some columns
        self.benchmark_col = Column.objects.create(
            table_name="PropertyState",
            column_name="Salesforce Benchmark ID",
            organization=self.org,
            is_extra_data=True,
        )

        self.another_col = Column.objects.create(
            table_name="PropertyState",
            column_name="Another Field",
            organization=self.org,
            is_extra_data=True,
        )

        self.sf_config = SalesforceConfig.objects.create(
            organization=self.org,
            compliance_label=self.compliance_label,
            indication_label=self.ind_label,
            violation_label=self.violation_label,
            seed_benchmark_id_column=self.benchmark_col,
            unique_benchmark_id_fieldname="Salesforce_Benchmark_ID__c",
            status_fieldname="Status__c",
        )

    def test_save_salesforce_config_perms(self):
        # use new org b/c can only have 1 config record on an org
        temp_org, _, _ = create_organization(self.root_owner_user)
        # add child  member to this new org
        temp_org.access_level_names = ["root", "child"]
        temp_child_level_instance = temp_org.add_new_access_level_instance(temp_org.root.id, "child")
        temp_org.add_member(self.child_member_user, temp_child_level_instance.pk, ROLE_MEMBER)
        temp_org.save()

        ind_label = Label.objects.create(name="Indication Label", super_organization=temp_org)
        violation_label = Label.objects.create(name="Violation Label", super_organization=temp_org)
        compliance_label = Label.objects.create(name="Compliance Label", super_organization=temp_org)

        status_fieldname = "Status__Yay__c"

        payload_data = {
            "indication_label": ind_label.id,
            "violation_label": violation_label.id,
            "compliance_label": compliance_label.id,
            "unique_benchmark_id_fieldname": "Salesforce_Benchmark_ID__c",
            "status_fieldname": status_fieldname,
        }

        # create
        url = reverse("api:v3:salesforce_configs-list") + "?organization_id=" + str(temp_org.id)
        # (child) member cannot (permission denied vs. not found)
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(payload_data), content_type="application/json")
        assert response.status_code == 403

        self.login_as_root_owner()
        response = self.client.post(url, data=json.dumps(payload_data), content_type="application/json")
        assert response.status_code == 200
        data = json.loads(response.content)

        # get detail
        new_data = data["salesforce_config"]
        sf_id = data["salesforce_config"]["id"]
        url = reverse("api:v3:salesforce_configs-detail", args=[sf_id]) + f"?organization_id={temp_org.pk}"

        # child member cannot
        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200

        # edit
        new_data["status_fieldname"] = "A_new_fieldname__c"
        # child member cannot
        self.login_as_child_member()
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        assert response.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        assert response.status_code == 200

    def test_save_salesforce_mapping_perms(self):
        # test saving salesforce mappings (root member only)
        self.energystar_col = Column.objects.create(
            table_name="PropertyState", column_name="ENERGY STAR Score", organization=self.org, is_extra_data=True
        )

        # create new mapping
        payload_data = {"salesforce_fieldname": "ENERGY_STAR_Score__c", "column": self.another_col.id}

        # child member cannot (permission denied)
        self.login_as_child_member()
        response = self.client.post(
            reverse("api:v3:salesforce_mappings-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        assert response.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.post(
            reverse("api:v3:salesforce_mappings-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(payload_data),
            content_type="application/json",
        )
        assert response.status_code == 200

        self.mapping_energystar = SalesforceMapping.objects.filter(salesforce_fieldname="ENERGY_STAR_Score__c").first()

        # Edit salesforce mappings
        new_data = {"salesforce_fieldname": "the_new_field__c"}
        url = reverse("api:v3:salesforce_mappings-detail", args=[self.mapping_energystar.pk]) + f"?organization_id={self.org.pk}"

        # child member cannot
        self.login_as_child_member()
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        assert response.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.put(url, json.dumps(new_data), content_type="application/json")
        assert response.status_code == 200

        # Delete salesforce mapping
        # child member cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 200

    def test_property_update_salesforce_perms(self):
        state = self.property_state_factory.get_property_state()

        # this ID should be valid for the test salesforce sandbox
        state.extra_data["Salesforce Benchmark ID"] = "a01Ea00000VqqMf"
        # add other Instance specific mappings for testing
        state.extra_data["Property GFA - Calculated (Buildings and Parking) (ft2)"] = state.gross_floor_area
        state.save()

        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        self.api_view.add_labels(self.api_view.models["property"].objects.none(), "property", [view.id], [self.ind_label.id])
        self.api_view.add_labels(self.api_view.models["property"].objects.none(), "property", [view.id], [self.compliance_label.id])

        # enable sf
        self.sf_config.url = SF_INSTANCE
        self.sf_config.username = SF_USERNAME
        self.sf_config.password = encrypt(SF_PASSWORD)
        self.sf_config.security_token = SF_SECURITY_TOKEN
        if SF_DOMAIN == "test":
            self.sf_config.domain = SF_DOMAIN
        self.sf_config.save()

        url = reverse("api:v3:properties-update-salesforce") + f"?organization_id={self.org.pk}"
        params = json.dumps({"property_view_ids": [view.id]})

        # child member cannot update parent property
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 404

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
