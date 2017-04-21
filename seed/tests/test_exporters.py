# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import uuid

import unicodecsv as csv
import xlrd
from django.db.models import Manager
from django.test import TestCase

from seed.factory import SEEDFactory
from seed.lib.exporter import Exporter
from seed.models import CanonicalBuilding, BuildingSnapshot


class TestExporters(TestCase):
    """Tests for exporting data to various formats."""

    def setUp(self):
        self.snapshots = []
        self.maxDiff = None
        for x in range(50):
            cb = CanonicalBuilding()
            cb.save()
            b = SEEDFactory.building_snapshot(canonical_building=cb)
            b.extra_data = {
                'my new field': 'something extra'
            }
            b.save()
            self.snapshots.append(b)

    def test_data_model_assumptions(self):
        """
        Some parts of export make certain assumptions about the data model,
        this test ensures that those assumptions are true.
        """
        self.assertTrue(hasattr(BuildingSnapshot, 'project_building_snapshots'))

    def test_csv_export(self):
        """Ensures exported CSV data matches source data"""
        qs_filter = {"pk__in": [x.pk for x in self.snapshots]}
        qs = BuildingSnapshot.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        fields = list(Exporter.fields_from_queryset(qs))
        raw = ['owner_address', 'owner_postal_code', 'owner_email', 'postal_code', 'occupied_floor_area',
               'custom_id_1', 'extra_data', 'state_province', 'tax_lot_id', 'address_line_2',
               'address_line_1', 'lot_number', 'year_ending', 'property_notes', 'generation_date',
               'energy_alerts', 'space_alerts', 'site_eui_weather_normalized', 'created', 'energy_score',
               'block_number', 'building_count', 'owner', 'source_eui', 'extra_data_sources', 'city',
               'confidence', 'district', 'best_guess_confidence', 'site_eui', 'building_certification',
               'modified', 'match_type', 'source_eui_weather_normalized', u'id', 'property_name',
               'conditioned_floor_area', 'pm_property_id', 'use_description', 'source_type', 'year_built',
               'release_date', 'gross_floor_area', 'owner_city_state', 'owner_telephone',
               'recent_sale_date']
        self.assertItemsEqual(fields, raw)

        fields.append("canonical_building__id")

        export_filename = exporter.export_csv(qs, fields)
        self.assertTrue(os.path.exists(export_filename))
        export_file = open(export_filename)

        reader = csv.reader(export_file)
        header = reader.next()

        self.assertEqual(header[len(fields) - 1], 'ID')

        for i in range(len(self.snapshots)):
            row = reader.next()
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
                csv_val = row[j]
                self.assertEqual(qs_val, csv_val)

        export_file.close()
        os.remove(export_filename)

    def test_csv_export_extra_data(self):
        """Ensures exported CSV data matches source data"""
        qs_filter = {"pk__in": [x.pk for x in self.snapshots]}
        qs = BuildingSnapshot.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        fields = list(Exporter.fields_from_queryset(qs))
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

    def test_xls_export(self):
        """Ensures exported XLS data matches source data"""
        qs_filter = {"pk__in": [x.pk for x in self.snapshots]}
        qs = BuildingSnapshot.objects.filter(**qs_filter)

        export_id = str(uuid.uuid4())
        exporter = Exporter(export_id, 'test_export', 'csv')

        fields = list(Exporter.fields_from_queryset(qs))
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
        for x in self.snapshots:
            x.delete()
