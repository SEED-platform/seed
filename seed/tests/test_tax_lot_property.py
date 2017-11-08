# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.models import (
    Cycle,
    PropertyView,
    TaxLotProperty,
)
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory
)


class TestTaxLotProperty(TestCase):
    """Tests for exporting data to various formats."""

    def setUp(self):
        self.properties = []
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.org = Organization.objects.create()
        # create a default cycle
        self.cycle = Cycle.objects.filter(organization_id=self.org).first()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.property_factory = FakePropertyFactory(
            organization=self.org
        )
        self.property_state_factory = FakePropertyStateFactory(
            organization=self.org
        )
        self.property_view_factory = FakePropertyViewFactory(
            organization=self.org, user=self.user
        )
        self.label_factory = FakeStatusLabelFactory(
            organization=self.org
        )
        self.property_view = self.property_view_factory.get_property_view()
        self.urls = ['http://example.com', 'http://example.org']
        self.client.login(**user_details)

    def test_tax_lot_property_get_related(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        qs_filter = {"pk__in": self.properties}
        qs = PropertyView.objects.filter(**qs_filter)

        columns = [
            'address_line_1', 'generation_date', 'energy_alerts', 'space_alerts',
            'building_count', 'owner', 'source_eui', 'jurisdiction_tax_lot_id',
            'city', 'confidence', 'district', 'best_guess_confidence',
            'site_eui', 'building_certification', 'modified', 'match_type',
            'source_eui_weather_normalized', u'id', 'property_name', 'conditioned_floor_area',
            'pm_property_id', 'use_description', 'source_type', 'year_built', 'release_date',
            'gross_floor_area', 'owner_city_state', 'owner_telephone', 'recent_sale_date',
        ]
        data = TaxLotProperty.get_related(qs, columns)

        self.assertEqual(len(data), 50)
        self.assertEqual(len(data[0]['related']), 0)

    def test_csv_export(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = [
            'address_line_1', 'generation_date', 'energy_alerts', 'space_alerts',
            'building_count', 'owner', 'source_eui', 'jurisdiction_tax_lot_id',
            'city', 'confidence', 'district', 'best_guess_confidence',
            'site_eui', 'building_certification', 'modified', 'match_type',
            'source_eui_weather_normalized', u'id', 'property_name', 'conditioned_floor_area',
            'pm_property_id', 'use_description', 'source_type', 'year_built', 'release_date',
            'gross_floor_area', 'owner_city_state', 'owner_telephone', 'recent_sale_date',
        ]

        # call the API
        url = reverse_lazy('api:v2.1:tax_lot_properties-csv')
        response = self.client.post(
            url + '?{}={}&{}={}&{}={}'.format(
                'organization_id', self.org.pk,
                'cycle_id', self.cycle,
                'inventory_type', 'properties'
            ),
            data=json.dumps({'columns': columns}),
            content_type='application/json'
        )

        # parse the content as array
        data = response.content.split('\n')

        self.assertTrue('address_line_1' in data[0].split(','))
        self.assertTrue('property_labels' in data[0].split(','))

        self.assertEqual(len(data), 53)
        # last row should be blank
        self.assertEqual(data[52], '')

    def tearDown(self):
        for x in self.properties:
            PropertyView.objects.get(pk=x).delete()
