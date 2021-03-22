# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>', Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""
from django.db import IntegrityError
from django.db import transaction

from seed.models import (
    ASSESSED_RAW,
    Property,
    PropertyView,
    StatusLabel as Label,
    TaxLot,
    TaxLotView,
)
from seed.models.data_quality import DataQualityCheck, Rule
from seed.tests.util import DataMappingBaseTestCase
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.utils.organizations import create_organization
from seed.views.v3.label_inventories import (
    LabelInventoryViewSet,
)


class TestLabelIntegrityChecks(DataMappingBaseTestCase):
    def setUp(self):
        self.api_view = LabelInventoryViewSet()

        # Models can't  be imported directly hence self
        self.PropertyViewLabels = self.api_view.models['property']
        self.TaxlotViewLabels = self.api_view.models['taxlot']

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }

        self.user, self.org, _import_file, _import_record, self.cycle = self.set_up(ASSESSED_RAW)

        org_2, _, _ = create_organization(self.user)
        self.org_2_status_label = Label.objects.create(
            name='org_2_label', super_organization=org_2
        )

    def test_error_occurs_when_trying_to_apply_a_label_to_propertyview_from_a_different_org(self):
        org_1_property = Property.objects.create(organization=self.org)
        property_state_factory = FakePropertyStateFactory(organization=self.org)
        org_1_propertystate = property_state_factory.get_property_state()
        org_1_propertyview = PropertyView.objects.create(
            property=org_1_property,
            state=org_1_propertystate,
            cycle=self.cycle
        )

        # Via Label API View
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    self.api_view.models['property'].objects.none(),
                    'property',
                    [org_1_propertyview.id],
                    [self.org_2_status_label.id]
                )

        # Via PropertyView Model
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_propertyview.labels.add(self.org_2_status_label)

        # Via PropertyState Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_ps_rule = org_1_dq.rules.filter(table_name='PropertyState').first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_ps_rule.status_label = self.org_2_status_label
        org_1_ps_rule.save()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_dq.update_status_label(
                    self.PropertyViewLabels,
                    Rule.objects.get(pk=org_1_ps_rule.id),
                    org_1_propertyview.id,
                    org_1_propertystate.id
                )

        self.assertFalse(PropertyView.objects.get(pk=org_1_propertyview.id).labels.all().exists())

    def test_error_occurs_when_trying_to_apply_a_label_to_taxlotview_from_a_different_org(self):
        org_1_taxlot = TaxLot.objects.create(organization=self.org)
        taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        org_1_taxlotstate = taxlot_state_factory.get_taxlot_state()
        org_1_taxlotview = TaxLotView.objects.create(
            taxlot=org_1_taxlot,
            state=org_1_taxlotstate,
            cycle=self.cycle
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    qs=self.api_view.models['taxlot'].objects.none(),
                    inventory_type='taxlot',
                    inventory_ids=[org_1_taxlotview.id],
                    add_label_ids=[self.org_2_status_label.id]
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_taxlotview.labels.add(self.org_2_status_label)

        # Via TaxLotState Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_tls_rule = org_1_dq.rules.filter(table_name='TaxLotState').first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_tls_rule.status_label = self.org_2_status_label
        org_1_tls_rule.save()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_dq.update_status_label(
                    label_class=self.TaxlotViewLabels,
                    rule=Rule.objects.get(pk=org_1_tls_rule.id),
                    linked_id=org_1_taxlotview.id,
                    row_id=org_1_taxlotstate.id
                )

        self.assertFalse(TaxLotView.objects.get(pk=org_1_taxlotview.id).labels.all().exists())
