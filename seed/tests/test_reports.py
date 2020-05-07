# !/usr/bin/env python
# encoding: utf-8

import datetime

from django.urls import reverse
from django.utils import timezone

from seed.models import (
    ASSESSED_RAW,
    Property,
    PropertyState,
    PropertyView
)
from seed.tests.util import DataMappingBaseTestCase
from seed.test_helpers.fake import FakeCycleFactory

from xlrd import open_workbook


class ExportReport(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        # cycle_1 starts 2015
        self.user, self.org, _import_file, _import_record, self.cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

    def test_report_export_excel_workbook(self):
        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        start = datetime.datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone())
        # import pdb; pdb.set_trace()
        self.cycle_2 = cycle_factory.get_cycle(name="Cycle 2", start=start)

        # create 5 records with site_eui and gross_floor_area in each cycle
        for i in range(1, 6):
            ps_a = PropertyState.objects.create(
                organization_id=self.org.id,
                site_eui=i,
                gross_floor_area=i * 100
            )
            property_a = Property.objects.create(organization_id=self.org.id)
            PropertyView.objects.create(
                state_id=ps_a.id,
                property_id=property_a.id,
                cycle_id=self.cycle.id
            )

            ps_b = PropertyState.objects.create(
                organization_id=self.org.id,
                site_eui=i,
                gross_floor_area=i * 100
            )
            property_b = Property.objects.create(organization_id=self.org.id)
            PropertyView.objects.create(
                state_id=ps_b.id,
                property_id=property_b.id,
                cycle_id=self.cycle_2.id
            )

        url = reverse('api:v2:export_reports_data')

        # needs to be turned into post?
        response = self.client.get(url + '?{}={}&{}={}&{}={}&{}={}&{}={}&{}={}&{}={}'.format(
            'organization_id', self.org.pk,
            'start', '2014-12-31T00:00:00-07:53',
            'end', '2017-12-31T00:00:00-07:53',
            'x_var', 'site_eui',
            'x_label', 'Site EUI',
            'y_var', 'gross_floor_area',
            'y_label', 'Gross Floor Area'
        ))

        self.assertEqual(200, response.status_code)

        wb = open_workbook(file_contents=response.content)

        # Spot check each sheet
        counts_sheet = wb.sheet_by_index(0)
        self.assertEqual('Counts', counts_sheet.name)

        # check count of properties with data
        self.assertEqual('Properties with Data', counts_sheet.cell(0, 1).value)
        self.assertEqual(5, counts_sheet.cell(1, 1).value)
        self.assertEqual(5, counts_sheet.cell(2, 1).value)

        raw_sheet = wb.sheet_by_index(1)
        self.assertEqual('Raw', raw_sheet.name)

        # check Site EUI values
        self.assertEqual('Site EUI', raw_sheet.cell(0, 1).value)
        self.assertEqual(1, raw_sheet.cell(1, 1).value)
        self.assertEqual(2, raw_sheet.cell(2, 1).value)

        agg_sheet = wb.sheet_by_index(2)
        self.assertEqual('Agg', agg_sheet.name)

        # check Gross Floor Area values
        self.assertEqual('Gross Floor Area', agg_sheet.cell(0, 1).value)
        self.assertEqual('0-99k', agg_sheet.cell(1, 1).value)
        self.assertEqual('0-99k', agg_sheet.cell(2, 1).value)
