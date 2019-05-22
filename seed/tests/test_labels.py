# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pipermerriam@gmail.com>', Paul Munday<paul@paulmunday.net>

Unit tests for seed/views/labels.py
"""
from django.db import IntegrityError
from django.db import transaction

from seed.landing.models import SEEDUser as User
from seed.models import (
    Property,
    StatusLabel as Label,
    TaxLot,
)
from seed.models.data_quality import DataQualityCheck, Rule
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization
from seed.views.labels import (
    UpdateInventoryLabelsAPIView,
)


class TestLabelIntegrityChecks(DeleteModelsTestCase):
    def setUp(self):
        self.api_view = UpdateInventoryLabelsAPIView()

        # Models can't  be imported directly hence self
        self.PropertyLabels = self.api_view.models['property']
        self.TaxlotLabels = self.api_view.models['taxlot']

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**self.user_details)
        self.org, _, _ = create_organization(self.user)

        org_2, _, _ = create_organization(self.user)
        self.org_2_status_label = Label.objects.create(
            name='org_2_label', super_organization=org_2
        )

    def test_error_occurs_when_trying_to_apply_a_label_to_property_from_a_different_org(self):
        org_1_property = Property.objects.create(organization=self.org)

        # Via Label API View
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    self.api_view.models['property'].objects.none(),
                    'property',
                    [org_1_property.id],
                    [self.org_2_status_label.id]
                )

        # Via Property Model
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_property.labels.add(self.org_2_status_label)

        # Via PropertyState Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_ps_rule = org_1_dq.rules.filter(table_name='PropertyState').first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_ps_rule.status_label = self.org_2_status_label
        org_1_ps_rule.save()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_dq.update_status_label(
                    self.PropertyLabels,
                    Rule.objects.get(pk=org_1_ps_rule.id),
                    org_1_property.id,
                )

        self.assertFalse(Property.objects.get(pk=org_1_property.id).labels.all().exists())

    def test_error_occurs_when_trying_to_apply_a_label_to_taxlot_from_a_different_org(self):
        # Repeat for TaxLot
        org_1_taxlot = TaxLot.objects.create(organization=self.org)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.api_view.add_labels(
                    self.api_view.models['taxlot'].objects.none(),
                    'taxlot',
                    [org_1_taxlot.id],
                    [self.org_2_status_label.id]
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_taxlot.labels.add(self.org_2_status_label)

        # Via TaxLot Rule with Label
        org_1_dq = DataQualityCheck.objects.get(organization=self.org)
        org_1_tls_rule = org_1_dq.rules.filter(table_name='TaxLotState').first()
        # Purposely give an Org 1 Rule an Org 2 Label
        org_1_tls_rule.status_label = self.org_2_status_label
        org_1_tls_rule.save()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                org_1_dq.update_status_label(
                    self.TaxlotLabels,
                    Rule.objects.get(pk=org_1_tls_rule.id),
                    org_1_taxlot.id,
                )

        self.assertFalse(TaxLot.objects.get(pk=org_1_taxlot.id).labels.all().exists())
