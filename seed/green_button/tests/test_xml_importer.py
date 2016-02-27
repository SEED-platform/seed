# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
from os import path

from seed.audit_logs.models import AuditLog
from django.test import TestCase
from seed.green_button import xml_importer
from seed.data_importer.models import ImportRecord, ImportFile
from seed.models import (
    BuildingSnapshot, TimeSeries
)
import seed.models
import xmltodict
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from django.core.files import File



# sample data corresponds to the data that should be extracted by
# xml_importer.building_data when called with the file
# green_button/tests/data/sample_gb_gas.xml
sample_meter_data = {
    'currency': '840',
    'power_of_ten_multiplier': '-3',
    'uom': '169'
}

sample_reading_data = [
    {
        'cost': '190923',
        'value': '2083',
        'start_time': '1357027200',
        'duration': '86400'
    },
    {
        'cost': '190923',
        'value': '2083',
        'start_time': '1357113600',
        'duration': '86400'
    }
]

sample_block_data = {
    'start_time': '1357027200',
    'duration': '31622400',
    'readings': sample_reading_data
}

sample_building_data = {
    'address': '635 ELM ST EL CERRITO CA 94530-3120',
    'service_category': '1',
    'meter': sample_meter_data,
    'interval': sample_block_data
}


class GreenButtonXMLParsingTests(TestCase):
    """
    Tests helper functions for pulling green button building data out
    of xml snippets.
    """

    def setUp(self):
        self.sample_xml_file = File(
            open(

                path.join(
                    path.dirname(__file__), 'data', 'sample_gb_gas.xml')
            )
        )

        self.sample_xml = self.sample_xml_file.read()

    def tearDown(self):
        self.sample_xml_file.close()

    def assert_fn_mapping(self, fn, mapping):
        """
        Takes a function fn and a mapping from input values to expected
        output values. Asserts that fn returns the expected output for
        each of the input values.
        """
        for inval, outval in mapping.iteritems():
            self.assertEquals(fn(inval), outval)

    def test_energy_type(self):
        """
        Test of xml_importer.energy_type.
        """
        expected_mappings = {
            -1: None,  # missing keys should return None
            0: seed.models.ELECTRICITY,
            1: seed.models.NATURAL_GAS
        }

        self.assert_fn_mapping(xml_importer.energy_type, expected_mappings)

    def test_energy_units(self):
        """
        Test of function that converts a green button 'uom'
        (unit of measurement?) integer to one of seed.models.ENERGY_UNITS.
        """
        expected_mappings = {
            -1: None,  # missing keys should return None
            72: seed.models.WATT_HOURS,
            169: seed.models.THERMS
        }

        self.assert_fn_mapping(xml_importer.energy_units, expected_mappings)

    def test_as_collection(self):
        """
        Test of xml_importer.as_collection.
        """
        self.assertEquals(xml_importer.as_collection(None), None)
        self.assertEquals(xml_importer.as_collection(1), [1])
        self.assertEquals(xml_importer.as_collection('1'), ['1'])
        self.assertEquals(xml_importer.as_collection([1]), [1])
        self.assertEquals(xml_importer.as_collection(['1']), ['1'])

    def test_interval_data(self):
        """
        Test of xml_importer.interval_data.
        """

        interval_xml = """
        <IntervalReading>
          <cost>190923</cost>
          <timePeriod>
            <duration>86400</duration>
            <start>1357027200</start>
          </timePeriod>
          <value>2083</value>
        </IntervalReading>
        """

        xml_data = xmltodict.parse(interval_xml)['IntervalReading']

        expected = {
            'cost': '190923',
            'value': '2083',
            'start_time': '1357027200',
            'duration': '86400'
        }

        self.assertEqual(xml_importer.interval_data(xml_data), expected)

    def test_meter_data(self):
        """
        Test of xml_importer.meter_data.
        """

        meter_xml = """
        <entry>
          <id>urn:uuid:4e1226d5-5172-3fdf-adf6-4001aee94849</id>
          <link href="/v1/ReadingType/1" rel="self">
          </link>
          <updated>2014-01-31T02:31:22.717Z</updated>
          <published>2011-11-30T12:00:00.000Z</published>
          <content type="xml">
            <ReadingType xmlns="http://naesb.org/espi">
              <currency>840</currency>
              <powerOfTenMultiplier>-3</powerOfTenMultiplier>
              <uom>169</uom>
            </ReadingType>
          </content>
        </entry>
        """

        xml_data = xmltodict.parse(meter_xml)['entry']

        expected = {
            'currency': '840',
            'power_of_ten_multiplier': '-3',
            'uom': '169'
        }

        self.assertEqual(xml_importer.meter_data(xml_data), expected)

    def test_interval_block_data(self):
        """
        Test of xml_importer.interval_block_data.
        """

        interval_block_start = """
        <IntervalBlock xmlns="http://naesb.org/espi">
          <interval>
            <duration>31622400</duration>
            <start>1357027200</start>
          </interval>
        """

        interval_block_end = """
        </IntervalBlock>
        """

        interval_reading_xml = """
        <IntervalReading>
          <cost>190923</cost>
          <timePeriod>
            <duration>86400</duration>
            <start>1357027200</start>
          </timePeriod>
          <value>2083</value>
        </IntervalReading>
        """

        single_ib_xml = (
            interval_block_start + interval_reading_xml + interval_block_end
        )

        multiple_ib_xml = (
            interval_block_start +
            interval_reading_xml + interval_reading_xml +
            interval_block_end
        )

        single_xml_data = xmltodict.parse(single_ib_xml)['IntervalBlock']
        multiple_xml_data = xmltodict.parse(multiple_ib_xml)['IntervalBlock']

        reading_expected = {
            'cost': '190923',
            'value': '2083',
            'start_time': '1357027200',
            'duration': '86400'
        }

        single_expected = {
            'start_time': '1357027200',
            'duration': '31622400',
            'readings': [reading_expected]
        }

        multiple_expected = copy.deepcopy(single_expected)
        multiple_expected['readings'] = [reading_expected, reading_expected]

        # test with single and multiple IntervalReadings; xmltodict
        # tries to get cute and may return a single dict or a list of
        # them for node contents
        single_res = xml_importer.interval_block_data(single_xml_data)
        multiple_res = xml_importer.interval_block_data(multiple_xml_data)

        self.assertEqual(single_res, single_expected)
        self.assertEqual(multiple_res, multiple_expected)

    def test_building_data(self):
        """
        Test of xml_importer.building_data.
        """
        xml_data = xmltodict.parse(self.sample_xml)

        expected_meter_data = {
            'currency': '840',
            'power_of_ten_multiplier': '-3',
            'uom': '169'
        }

        reading_expected = [
            {
                'cost': '190923',
                'value': '2083',
                'start_time': '1357027200',
                'duration': '86400'
            },
            {
                'cost': '190923',
                'value': '2083',
                'start_time': '1357113600',
                'duration': '86400'
            }
        ]

        expected_block_data = {
            'start_time': '1357027200',
            'duration': '31622400',
            'readings': reading_expected
        }

        expected = {
            'address': '635 ELM ST EL CERRITO CA 94530-3120',
            'service_category': '1',
            'meter': expected_meter_data,
            'interval': expected_block_data
        }

        data = xml_importer.building_data(xml_data)
        self.assertEqual(data, sample_building_data)


class GreenButtonXMLImportTests(TestCase):
    """
    Tests of various ways of authenticating to the API.

    Uses the get_building endpoint in all cases.
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.sample_xml_file = File(
            open(
                path.join(
                    path.dirname(__file__), 'data', 'sample_gb_gas.xml')
            )
        )

        self.sample_xml = self.sample_xml_file.read()

        self.import_record = ImportRecord.objects.create(
            name="Test Green Button Import",
            super_organization=self.org,
            owner=self.user,
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            file=self.sample_xml_file
        )

    def tearDown(self):
        self.sample_xml_file.close()

    def assert_models_created(self):
        """
        Tests that appropriate models for the sample xml file have
        been created.
        """
        # should create BuildingSnapshot, CanonicalBuilding, Meter,
        # and 2 TimeSeries
        bs = BuildingSnapshot.objects.get(
            address_line_1=sample_building_data['address']
        )
        cb = bs.canonical_building
        meters = bs.meters.all()
        self.assertEqual(len(meters), 1)

        meter = meters.first()
        tss = TimeSeries.objects.filter(meter=meter)
        self.assertEqual(len(tss), 2)

    def test_create_models(self):
        """
        Test of xml_importer.create_models.
        """
        xml_data = xmltodict.parse(self.sample_xml)
        b_data = xml_importer.building_data(xml_data)

        # no audit logs should exist yet, testing this way because it
        # is hard to assert what the content_object of an AuditLog is
        logs = AuditLog.objects.all()
        self.assertEqual(logs.count(), 0)
        cb = xml_importer.create_models(b_data, self.import_file)
        logs = AuditLog.objects.all()
        self.assert_models_created()
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.organization, self.org)

    def test_import_xml(self):
        """
        Test of xml_importer.import_xml.
        """
        xml_importer.import_xml(self.import_file)
        self.assert_models_created()
