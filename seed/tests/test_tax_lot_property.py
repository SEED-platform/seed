# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import (
    Cycle,
    PropertyView,
    TaxLotProperty,
    Column,
    Note,
)
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory
)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization
from xlrd import open_workbook


class TestTaxLotProperty(DataMappingBaseTestCase):
    """Tests for exporting data to various formats."""

    def setUp(self):
        self.properties = []
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.org, _, _ = create_organization(self.user)
        # create a default cycle
        self.cycle = Cycle.objects.filter(organization_id=self.org).first()
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
            'city', 'district', 'site_eui', 'building_certification', 'modified', 'match_type',
            'source_eui_weather_normalized', 'id', 'property_name', 'conditioned_floor_area',
            'pm_property_id', 'use_description', 'source_type', 'year_built', 'release_date',
            'gross_floor_area', 'owner_city_state', 'owner_telephone', 'recent_sale_date',
        ]
        columns_from_database = Column.retrieve_all(self.org.id, 'property', False)
        data = TaxLotProperty.get_related(qs, columns, columns_from_database)

        self.assertEqual(len(data), 50)
        self.assertEqual(len(data[0]['related']), 0)

    def test_csv_export(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, 'property', False):
            columns.append(c['name'])

        # call the API
        url = reverse_lazy('api:v2.1:tax_lot_properties-export')
        response = self.client.post(
            url + '?{}={}&{}={}&{}={}'.format(
                'organization_id', self.org.pk,
                'cycle_id', self.cycle,
                'inventory_type', 'properties'
            ),
            data=json.dumps({'columns': columns, 'export_type': 'csv'}),
            content_type='application/json'
        )

        # parse the content as array
        data = response.content.decode('utf-8').split('\n')

        self.assertTrue('Address Line 1' in data[0].split(','))
        self.assertTrue('Property Labels\r' in data[0].split(','))

        self.assertEqual(len(data), 53)
        # last row should be blank
        self.assertEqual(data[52], '')

    def test_csv_export_with_notes(self):
        multi_line_note = self.property_view.notes.create(name='Manually Created', note_type=Note.NOTE, text='multi\nline\nnote')
        single_line_note = self.property_view.notes.create(name='Manually Created', note_type=Note.NOTE, text='single line')

        self.properties.append(self.property_view.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, 'property', False):
            columns.append(c['name'])

        # call the API
        url = reverse_lazy('api:v2.1:tax_lot_properties-export')
        response = self.client.post(
            url + '?{}={}&{}={}&{}={}'.format(
                'organization_id', self.org.pk,
                'cycle_id', self.cycle,
                'inventory_type', 'properties'
            ),
            data=json.dumps({'columns': columns, 'export_type': 'csv'}),
            content_type='application/json'
        )

        # parse the content as array
        data = response.content.decode('utf-8').split('\r\n')
        notes_string = (
            multi_line_note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p") + "\n" +
            multi_line_note.text +
            "\n----------\n" +
            single_line_note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p") + "\n" +
            single_line_note.text
        )

        self.assertEqual(len(data), 3)
        self.assertTrue('Property Notes' in data[0].split(','))

        self.assertTrue(notes_string in data[1])

    def test_xlxs_export(self):
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, 'property', False):
            columns.append(c['name'])

        # call the API
        url = reverse_lazy('api:v2.1:tax_lot_properties-export')
        response = self.client.post(
            url + '?{}={}&{}={}&{}={}'.format(
                'organization_id', self.org.pk,
                'cycle_id', self.cycle,
                'inventory_type', 'properties'
            ),
            data=json.dumps({'columns': columns, 'export_type': 'xlsx'}),
            content_type='application/json'
        )

        # parse the content as array
        wb = open_workbook(file_contents=response.content)

        data = [row.value for row in wb.sheet_by_index(0).row(0)]

        self.assertTrue('Address Line 1' in data)
        self.assertTrue('Property Labels' in data)

        self.assertEqual(len([r for r in wb.sheet_by_index(0).get_rows()]), 52)

    def test_json_export(self):
        """Test to make sure get_related returns the fields"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        columns = []
        for c in Column.retrieve_all(self.org.id, 'property', False):
            columns.append(c['name'])

        # call the API
        url = reverse_lazy('api:v2.1:tax_lot_properties-export')
        response = self.client.post(
            url + '?{}={}&{}={}&{}={}'.format(
                'organization_id', self.org.pk,
                'cycle_id', self.cycle,
                'inventory_type', 'properties'
            ),
            data=json.dumps({'columns': columns, 'export_type': 'geojson'}),
            content_type='application/json'
        )

        # parse the content as dictionary
        data = json.loads(response.content)

        first_level_keys = list(data.keys())

        self.assertIn("type", first_level_keys)
        self.assertIn("crs", first_level_keys)
        self.assertIn("features", first_level_keys)

        record_level_keys = list(data['features'][0]['properties'].keys())

        self.assertIn('Address Line 1', record_level_keys)
        self.assertTrue('Gross Floor Area', record_level_keys)

        # ids 52 up to and including 102
        self.assertEqual(len(data['features']), 51)

    def tearDown(self):
        for x in self.properties:
            PropertyView.objects.get(pk=x).delete()
