"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Piper Merriam <pipermerriam@gmail.com>
:author Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""

import json

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse_lazy

from seed.models import ASSESSED_RAW, Property, PropertyView, TaxLot, TaxLotView
from seed.models import StatusLabel as Label
from seed.models.data_quality import DataQualityCheck, Rule
from seed.test_helpers.fake import FakePropertyStateFactory, FakeTaxLotStateFactory
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization
from seed.views.v3.label_inventories import LabelInventoryViewSet


class TestLabelIntegrityChecks(DataMappingBaseTestCase):
    def setUp(self):
        self.api_view = LabelInventoryViewSet()

        # Models can't  be imported directly hence self
        self.PropertyViewLabels = self.api_view.models["property"]
        self.TaxlotViewLabels = self.api_view.models["taxlot"]

        self.user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}

        self.user, self.org, _import_file, _import_record, self.cycle = self.set_up(ASSESSED_RAW)

        org_2, _, _ = create_organization(self.user)
        self.org_2_status_label = Label.objects.create(name="org_2_label", super_organization=org_2)

    def test_error_occurs_when_trying_to_apply_a_label_to_propertyview_from_a_different_org(self):
        org_1_property = Property.objects.create(organization=self.org)
        property_state_factory = FakePropertyStateFactory(organization=self.org)
        org_1_propertystate = property_state_factory.get_property_state()
        org_1_propertyview = PropertyView.objects.create(property=org_1_property, state=org_1_propertystate, cycle=self.cycle)

        # Via Label API View
        with transaction.atomic(), pytest.raises(IntegrityError):
            self.api_view.add_labels(
                self.api_view.models["property"].objects.none(), "property", [org_1_propertyview.id], [self.org_2_status_label.id]
            )

        # Via PropertyView Model
        with transaction.atomic(), pytest.raises(IntegrityError):
            org_1_propertyview.labels.add(self.org_2_status_label)

        # Via PropertyState Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_ps_rule = org_1_dq.rules.filter(table_name="PropertyState").first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_ps_rule.status_label = self.org_2_status_label
        org_1_ps_rule.save()

        with transaction.atomic(), pytest.raises(IntegrityError):
            org_1_dq.update_status_label(
                self.PropertyViewLabels, Rule.objects.get(pk=org_1_ps_rule.id), org_1_propertyview.id, org_1_propertystate.id
            )

        self.assertFalse(PropertyView.objects.get(pk=org_1_propertyview.id).labels.all().exists())

    def test_error_occurs_when_trying_to_apply_a_label_to_taxlotview_from_a_different_org(self):
        org_1_taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        org_1_taxlotstate = taxlot_state_factory.get_taxlot_state()
        org_1_taxlotview = TaxLotView.objects.create(taxlot=org_1_taxlot, state=org_1_taxlotstate, cycle=self.cycle)

        with transaction.atomic(), pytest.raises(IntegrityError):
            self.api_view.add_labels(
                qs=self.api_view.models["taxlot"].objects.none(),
                inventory_type="taxlot",
                inventory_ids=[org_1_taxlotview.id],
                add_label_ids=[self.org_2_status_label.id],
            )

        with transaction.atomic(), pytest.raises(IntegrityError):
            org_1_taxlotview.labels.add(self.org_2_status_label)

        # Via TaxLotState Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_tls_rule = org_1_dq.rules.filter(table_name="TaxLotState").first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_tls_rule.status_label = self.org_2_status_label
        org_1_tls_rule.save()

        with transaction.atomic(), pytest.raises(IntegrityError):
            org_1_dq.update_status_label(
                label_class=self.TaxlotViewLabels,
                rule=Rule.objects.get(pk=org_1_tls_rule.id),
                linked_id=org_1_taxlotview.id,
                row_id=org_1_taxlotstate.id,
            )

        self.assertFalse(TaxLotView.objects.get(pk=org_1_taxlotview.id).labels.all().exists())


class TestLabelViewSet(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

    def test_label_bulk_update(self):
        labels = Label.objects.all()
        show_in_list_count = labels.filter(show_in_list=True).count()
        assert show_in_list_count == 0

        label_ids = list(labels.values_list("id", flat=True))
        url = reverse_lazy("api:v3:labels-bulk-update") + "?organization_id=" + str(self.org.id)
        data = {"label_ids": label_ids, "data": {"show_in_list": True}}
        self.client.put(url, data=json.dumps(data), content_type="application/json")
        show_in_list_count = Label.objects.filter(show_in_list=True).count()
        assert show_in_list_count == Label.objects.count()

        data["data"]["show_in_list"] = False
        self.client.put(url, data=json.dumps(data), content_type="application/json")
        show_in_list_count = Label.objects.filter(show_in_list=True).count()
        assert show_in_list_count == 0
