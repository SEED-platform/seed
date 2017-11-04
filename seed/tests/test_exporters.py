# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import uuid

import unicodecsv as csv
import xlrd
from django.db.models import Manager
from django.test import TestCase
from unittest import skip

from seed.landing.models import SEEDUser as User
from seed.lib.exporter import Exporter
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.models import (
    PropertyView,

)
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeStatusLabelFactory
)


class TestExporters(TestCase):
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

    def test_csv_export(self):
        """Ensures exported CSV data matches source data"""
        for i in range(50):
            p = self.property_view_factory.get_property_view()
            self.properties.append(p.id)

        qs_filter = {"pk__in": self.properties}
        qs = PropertyView.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        state_fields = [
            'owner_address', 'owner_postal_code', 'owner_email', 'postal_code',
            'occupied_floor_area', 'custom_id_1', 'state_province', 'tax_lot_id',
            'address_line_2', 'address_line_1', 'lot_number', 'year_ending', 'property_notes',
            'generation_date', 'energy_alerts', 'space_alerts', 'site_eui_weather_normalized',
            'created', 'energy_score', 'block_number', 'building_count', 'owner', 'source_eui',
            'city', 'confidence', 'district', 'best_guess_confidence',
            'site_eui', 'building_certification', 'modified', 'match_type',
            'source_eui_weather_normalized', u'id', 'property_name', 'conditioned_floor_area',
            'pm_property_id', 'use_description', 'source_type', 'year_built', 'release_date',
            'gross_floor_area', 'owner_city_state', 'owner_telephone', 'recent_sale_date',
        ]

        export_filename = exporter.export_csv(qs, state_fields)
        print(export_filename)
        self.assertTrue(os.path.exists(export_filename))
        export_file = open(export_filename)

        reader = csv.reader(export_file)
        header = reader.next()

        # spot check the headers
        header_expected = [
            u'owner_address', u'owner_postal_code', u'owner_email', u'postal_code',
            u'occupied_floor_area', u'custom_id_1', u'state_province', u'tax_lot_id',
            u'address_line_2', u'address_line_1', u'lot_number', u'year_ending', u'property_notes',
            u'generation_date', u'energy_alerts', u'space_alerts', u'site_eui_weather_normalized',
            u'created', u'energy_score', u'block_number', u'building_count', u'owner',
            u'source_eui', u'city', u'confidence', u'district', u'best_guess_confidence',
            u'site_eui', u'building_certification', u'modified', u'match_type',
            u'source_eui_weather_normalized', u'ID', u'property_name', u'conditioned_floor_area',
            u'pm_property_id', u'use_description', u'source_type', u'year_built', u'release_date',
            u'gross_floor_area', u'owner_city_state', u'owner_telephone', u'recent_sale_date',
        ]
        self.assertListEqual(header, header_expected)

        # spot check some of the body
        row_1 = reader.next()

        export_file.close()
        os.remove(export_filename)

    @skip('To be updated with new data model')
    def test_csv_export_extra_data(self):
        """Ensures exported CSV data matches source data"""
        qs_filter = {"pk__in": [x.pk for x in self.snapshots]}
        qs = BuildingSnapshot.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        fields = list(Exporter._fields_from_queryset(qs))
        fields.append("canonical_building__id")
        fields.append('my new field')

        export_filename = exporter.export_csv(qs, fields)
        export_file = open(export_filename)

        reader = csv.reader(export_file)
        header = reader.next()

        self.assertEqual(header[len(fields) - 1], 'my new field')

        for i in range(len(self.snapshots)):
            row = reader.next()
            for j in range(len(fields)):
                field = fields[j]
                components = field.split("__")
                qs_val = qs[i]
                for component in components:
                    try:
                        qs_val = getattr(qs_val, component)
                    except AttributeError:
                        qs_val = qs_val.extra_data.get(component)
                    if qs_val is None:
                        break
                if isinstance(qs_val, Manager) or qs_val is None:
                    qs_val = u''
                else:
                    qs_val = unicode(qs_val)
                csv_val = row[j]
                self.assertEqual(qs_val, csv_val)

        export_file.close()
        os.remove(export_filename)

    @skip('To be updated with new data model')
    def test_xls_export(self):
        """Ensures exported XLS data matches source data"""
        qs_filter = {"pk__in": [x.pk for x in self.snapshots]}
        qs = BuildingSnapshot.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        fields = list(Exporter._fields_from_queryset(qs))
        fields.append("canonical_building__id")

        export_filename = exporter.export_xls(qs, fields)
        export_file = xlrd.open_workbook(export_filename)
        worksheet = export_file.sheet_by_name(export_file.sheet_names()[0])

        self.assertEqual(worksheet.cell_value(0, len(fields) - 1), 'ID')

        for i in range(len(self.snapshots)):
            for j in range(len(fields)):
                field = fields[j]
                components = field.split("__")
                qs_val = qs[i]
                for component in components:
                    qs_val = getattr(qs_val, component)
                    if qs_val is None:
                        break
                if isinstance(qs_val, Manager) or qs_val is None:
                    qs_val = u''
                else:
                    qs_val = unicode(qs_val)
                xls_val = worksheet.cell_value(i + 1, j)
                self.assertEqual(qs_val, xls_val)

    def tearDown(self):
        for x in self.properties:
            PropertyView.objects.get(pk=x).delete()
