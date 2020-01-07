# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    StatusLabel as Label,
)
from seed.utils.organizations import (
    create_organization
)


class TestOrganizationCreation(TestCase):

    def test_organization_creation_creates_default_labels(self):
        """Make sure last organization user is change to owner."""
        user = User.objects.create(email='test-user@example.com')
        org, org_user, user_added = create_organization(
            user=user,
            org_name='test-organization',
        )
        self.assertEqual(
            org.labels.count(),
            len(Label.DEFAULT_LABELS),
        )

    def test_organization_creation_creates_matching_criteria_columns(self):
        user = User.objects.create(email='test-user@example.com')
        org, org_user, user_added = create_organization(
            user=user,
            org_name='test-organization',
        )

        property_default_matchers = [
            'address_line_1',
            'custom_id_1',
            'pm_property_id',
            'ubid',
        ]

        taxlot_default_matchers = [
            'address_line_1',
            'custom_id_1',
            'jurisdiction_tax_lot_id',
            'ulid',
        ]

        property_matching_criteria = [
            col_obj.get('column_name')
            for col_obj
            in Column.objects.filter(organization_id=org.id, table_name='PropertyState', is_matching_criteria=True).values('column_name')
        ]

        taxlot_matching_criteria = [
            col_obj.get('column_name')
            for col_obj
            in Column.objects.filter(organization_id=org.id, table_name='TaxLotState', is_matching_criteria=True).values('column_name')
        ]

        self.assertCountEqual(property_default_matchers, property_matching_criteria)
        self.assertCountEqual(taxlot_default_matchers, taxlot_matching_criteria)
