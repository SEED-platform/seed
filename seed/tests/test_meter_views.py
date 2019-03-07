# !/usr/bin/env python
# encoding: utf-8

import ast
import os
import json

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import get_current_timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import save_raw_data
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.landing.models import SEEDUser as User
from seed.models import (
    PropertyState,
    PropertyView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
)
from seed.utils.organizations import create_organization


class TestMeterViewSet(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**self.user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        # pm_property_ids must match those within example-monthly-meter-usage.xlsx
        self.pm_property_id_1 = '5766973'
        self.pm_property_id_2 = '5766975'

        property_details['pm_property_id'] = self.pm_property_id_1
        state_1 = PropertyState(**property_details)
        state_1.save()
        self.state_1 = PropertyState.objects.get(pk=state_1.id)

        property_details['pm_property_id'] = self.pm_property_id_2
        state_2 = PropertyState(**property_details)
        state_2.save()
        self.state_2 = PropertyState.objects.get(pk=state_2.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_1 = self.property_factory.get_property()
        self.property_2 = self.property_factory.get_property()

        self.property_view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)
        self.property_view_2 = PropertyView.objects.create(property=self.property_2, cycle=self.cycle, state=self.state_2)

        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

    def test_parsed_meters_confirmation_verifies_energy_type_and_unit_parsed_from_column_headers(self):
        # TODO: very possible/likely that this endpoint should invalidate entries
        # but valid/invalid energy types and units may be changed before feature work ends
        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "column_header": "Electricity Use  (kBtu)",
                "parsed_type": "Electricity",
                "parsed_unit": "kBtu",
            },
            {
                "column_header": "Natural Gas Use  (GJ)",
                "parsed_type": "Natural Gas",
                "parsed_unit": "GJ",
            },
        ]

        self.assertEqual(result_dict.get("validated_type_units"), expectation)

    def test_parsed_meters_confirmation_returns_pm_property_ids_and_corresponding_incoming_counts(self):
        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "portfolio_manager_id": "5766973",
                "incoming": 4,
            },
            {
                "portfolio_manager_id": "5766975",
                "incoming": 4,
            },
        ]

        self.assertEqual(result_dict.get("proposed_imports"), expectation)

    def test_parsed_meters_confirmation_returns_unlinkable_pm_property_ids(self):
        PropertyState.objects.all().delete()

        url = reverse('api:v2:meters-parsed-meters-confirmation')

        post_params = json.dumps({
            'file_id': self.import_file.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = [
            {
                "portfolio_manager_id": "5766973",
            },
            {
                "portfolio_manager_id": "5766975",
            },
        ]

        self.assertCountEqual(result_dict.get("unlinkable_pm_ids"), expectation)

    def test_meter_readings_and_headers_return_by_property_energy_usage_given_property_view(self):
        save_raw_data(self.import_file.id)

        url = reverse('api:v2:meters-property-energy-usage')

        post_params = json.dumps({
            'property_view_id': self.property_view_1.id,
            'organization_id': self.org.pk,
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            'readings': [
                {
                    'start_time': '2016-01-01 00:00:00',
                    'end_time': '2016-01-31 23:59:59',
                    'Electricity': 597478.9,
                    'Natural Gas': 545942781.5634,
                },
                {
                    'start_time': '2016-02-01 00:00:00',
                    'end_time': '2016-02-29 23:59:59',
                    'Electricity': 548603.7,
                    'Natural Gas': 462534790.7817,
                },
            ],
            'headers': [
                {
                    'field': 'start_time',
                },
                {
                    'field': 'end_time',
                },
                {
                    'field': 'Electricity',
                    'displayName': 'Electricity (kBtu)',
                    'cellFilter': 'number: 0',
                },
                {
                    'field': 'Natural Gas',
                    'displayName': 'Natural Gas (kBtu)',
                    'cellFilter': 'number: 0',
                },
            ]
        }

        self.assertCountEqual(result_dict['readings'], expectation['readings'])
        self.assertCountEqual(result_dict['headers'], expectation['headers'])


class TestMeterValidTypesUnits(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**self.user_details)

    def test_view_that_returns_valid_types_and_units_for_meters(self):
        url = reverse('api:v2:meters-valid-types-units')

        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

        self.assertEqual(result_dict, expectation)


#         """We throw an error when there's no building id passed in."""
#         client = APIClient()
#         client.login(username=self.user.username, password='secret')
#
#         url = reverse('api:v2:meters-list')
#
#         expected = {
#             "status": "error",
#             "message": "No property_view_id specified",
#             "meters": []
#         }
#
#         resp = client.get(url, {'organization_id': self.org.pk})
#
#         self.assertEqual(resp.status_code, status.HTTP_200_OK)
#         self.assertDictEqual(json.loads(resp.content), expected)
#
#     def test_get_meters(self):
#         """We get a meter that we saved back that was assigned to a property view"""
#         ps = PropertyState.objects.create(organization=self.org)
#         property_view = ps.promote(self.cycle)
#
#         meter = Meter.objects.create(
#             name='tester',
#             energy_type=Meter.ELECTRICITY,
#             energy_units=Meter.KILOWATT_HOURS,
#             property_view=property_view,
#         )
#
#         client = APIClient()
#         client.login(username=self.user.username, password='secret')
#
#         url = reverse('api:v2:meters-detail', args=(meter.pk,))
#         resp = client.get(url)
#
#         expected = {
#             "status": "success",
#             "meter": {
#                 "property_view": property_view.pk,
#                 "scenario": None,
#                 "name": "tester",
#                 "timeseries_count": 0,
#                 "energy_units": 1,
#                 "energy_type": 2,
#                 "pk": meter.pk,
#                 "model": "seed.meter",
#                 "id": meter.pk,
#             }
#         }
#
#         self.assertDictEqual(json.loads(resp.content), expected)
#
#     def test_add_meter_to_property(self):
#         """Add a meter to a building."""
#         ps = PropertyState.objects.create(organization=self.org)
#         pv = ps.promote(self.cycle)
#
#         data = {
#             "property_view_id": pv.pk,
#             "name": "test meter",
#             "energy_type": Meter.NATURAL_GAS,
#             "energy_units": Meter.KILOWATT_HOURS
#         }
#
#         client = APIClient()
#         client.login(username=self.user.username, password='secret')
#         url = reverse('api:v2:meters-list') + '?organization_id={}'.format(self.org.pk)
#         resp = client.post(url, data)
#
#         expected = {
#             "status": "success",
#             "meter": {
#                 "property_view": pv.pk,
#                 "name": "test meter",
#                 "energy_units": Meter.KILOWATT_HOURS,
#                 "energy_type": Meter.NATURAL_GAS,
#                 "model": "seed.meter",
#             }
#         }
#         self.assertEqual(json.loads(resp.content)['status'], "success")
#         self.assertDictContainsSubset(expected['meter'], json.loads(resp.content)['meter'])
#
#     def test_get_timeseries(self):
#         """We get all the times series for a meter."""
#         meter = Meter.objects.create(
#             name='test',
#             energy_type=Meter.ELECTRICITY,
#             energy_units=Meter.KILOWATT_HOURS
#         )
#
#         for i in range(100):
#             TimeSeries.objects.create(
#                 begin_time="2015-01-01T08:00:00.000Z",
#                 end_time="2015-01-01T08:00:00.000Z",
#                 reading=23,
#                 meter=meter
#             )
#
#         client = APIClient()
#         client.login(username=self.user.username, password='secret')
#         url = reverse('api:v2:meters-get-timeseries', args=(meter.pk,))
#         resp = client.get(url)
#
#         expected = {
#             "begin": "2015-01-01 08:00:00+00:00",
#             "end": "2015-01-01 08:00:00+00:00",
#             "value": 23.0,
#         }
#
#         jdata = json.loads(resp.content)
#         self.assertEqual(jdata['status'], "success")
#         self.assertEqual(len(jdata['meter']['data']), 100)
#         self.assertDictEqual(jdata['meter']['data'][0], expected)
#
#         # Not yet implemented
#         # def test_add_timeseries(self):
#         #     """Adding time series works."""
#         #     meter = Meter.objects.create(
#         #         name='test',
#         #         energy_type=Meter.ELECTRICITY,
#         #         energy_units=Meter.KILOWATT_HOURS
#         #     )
#         #
#         #     client = APIClient()
#         #     client.login(username=self.user.username, password='secret')
#         #     url = reverse('apiv2:meters-add-timeseries', args=(meter.pk,))
#         #
#         #     resp = client.post(url)
#         #
#         #             'timeseries': [
#         #                 {
#         #                     'begin_time': '2014-07-10T18:14:54.726Z',
#         #                     'end_time': '2014-07-10T18:14:54.726Z',
#         #                     'cost': 345,
#         #                     'reading': 23.0,
#         #                 },
#         #                 {
#         #                     'begin_time': '2014-07-09T18:14:54.726Z',
#         #                     'end_time': '2014-07-09T18:14:54.726Z',
#         #                     'cost': 33,
#         #                     'reading': 11.0,
#         #                 }
#         #
#         #             ]
#         #         })
#         #     )
#         #
#         #     self.assertEqual(TimeSeries.objects.all().count(), 0)
#         #
#         #     resp = json.loads(meters.add_timeseries(fake_request).content)
#
#         #     self.assertEqual(resp, {'status': 'success'})
#         #     self.assertEqual(TimeSeries.objects.all().count(), 2)
