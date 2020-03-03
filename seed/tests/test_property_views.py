# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import json

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)

from pytz import timezone

from seed.landing.models import SEEDUser as User
from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
)
from seed.models import (
    Meter,
    MeterReading,
    PropertyState,
    PropertyView,
    Column,
    BuildingFile,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakePropertyViewFactory,
    FakeColumnListSettingsFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization

COLUMNS_TO_SEND = [
    'project_id',
    'address_line_1',
    'city',
    'state_province',
    'postal_code',
    'pm_parent_property_id',
    'extra_data_field',
    'jurisdiction_tax_lot_id'
]


# These tests mostly use V2.1 API except for when writing back to the API for updates
class PropertyViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListSettingsFactory(organization=self.org)
        self.client.login(**user_details)

    def test_get_and_edit_properties(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }

        url = reverse('api:v2.1:properties-list') + '?cycle_id={}'.format(self.cycle.pk)
        response = self.client.get(url, params)
        data = json.loads(response.content)
        self.assertEqual(len(data['properties']), 1)
        result = data['properties'][0]
        self.assertEqual(result['state']['address_line_1'], state.address_line_1)

        db_created_time = result['created']
        db_updated_time = result['updated']
        self.assertTrue(db_created_time is not None)
        self.assertTrue(db_updated_time is not None)

        # update the address
        new_data = {
            "state": {
                "address_line_1": "742 Evergreen Terrace"
            }
        }
        url = reverse('api:v2:properties-detail', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')

        # the above call returns data from the PropertyState, need to get the Property --
        # call the get on the same API to retrieve it
        response = self.client.get(url, content_type='application/json')
        data = json.loads(response.content)
        # make sure the address was updated and that the datetimes were modified
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['state']['address_line_1'], '742 Evergreen Terrace')
        self.assertEqual(
            datetime.strptime(db_created_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0),
            datetime.strptime(data['property']['created'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0)
        )
        self.assertGreater(datetime.strptime(data['property']['updated'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                           datetime.strptime(db_updated_time, "%Y-%m-%dT%H:%M:%S.%fZ"))

    def test_list_properties_with_profile_id(self):
        state = self.property_state_factory.get_property_state(extra_data={"field_1": "value_1"})
        prprty = self.property_factory.get_property()
        PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(state)
        # get the columnlistsetting (default) for all columns
        columnlistsetting = self.column_list_factory.get_columnlistsettings(columns=['address_line_1', 'field_1'])

        params = {
            'organization_id': self.org.pk,
            'profile_id': columnlistsetting.id,
        }
        url = reverse('api:v2.1:properties-list') + '?cycle_id={}'.format(self.cycle.pk)
        response = self.client.get(url, params)
        data = response.json()
        self.assertEqual(len(data['properties']), 1)
        result = data['properties'][0]
        self.assertEqual(result['state']['address_line_1'], state.address_line_1)
        self.assertEqual(result['state']['extra_data']['field_1'], 'value_1')
        self.assertFalse(result['state'].get('city', None))

    def test_search_identifier(self):
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='123456')
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='987654 Long Street')
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1='123 Main Street')
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1='Hamilton Road',
                                                     analysis_state=PropertyState.ANALYSIS_STATE_QUEUED)
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='long road',
                                                     analysis_state=PropertyState.ANALYSIS_STATE_QUEUED)

        # Typically looks like this
        # http://localhost:8000/api/v2.1/properties/?organization_id=265&cycle=219&identifier=09-IS

        # check for all items
        query_params = "?cycle={}&organization_id={}".format(self.cycle.pk, self.org.pk)
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 5)

        # check for 2 items with 123
        query_params = "?cycle={}&organization_id={}&identifier={}".format(self.cycle.pk, self.org.pk, '123')
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        # print out the result of this when there are more than two in an attempt to catch the
        # non-deterministic part of this test
        if len(results) > 2:
            print(results)

        self.assertEqual(len(results), 2)

        # check the analysis states
        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(self.cycle.pk, self.org.pk, 'Completed')
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 0)

        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Not Started'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 3)

        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Queued'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 2)

        # check the combination of both the identifier and the analysis state
        query_params = "?cycle={}&organization_id={}&identifier={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Long', 'Queued'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 1)

    def test_meters_exist(self):
        # Create a property set with meters
        state_1 = self.property_state_factory.get_property_state()
        property_1 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=property_1, cycle=self.cycle, state=state_1
        )

        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": property_1.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # Create a property set without meters
        state_2 = self.property_state_factory.get_property_state()
        property_2 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=property_2, cycle=self.cycle, state=state_2
        )

        url = reverse('api:v2:properties-meters-exist')

        true_post_params = json.dumps({
            'inventory_ids': [property_2.pk, property_1.pk]
        })
        true_result = self.client.post(url, true_post_params, content_type='application/json')
        self.assertEqual(b'true', true_result.content)

        false_post_params = json.dumps({
            'inventory_ids': [property_2.pk]
        })
        false_result = self.client.post(url, false_post_params, content_type='application/json')
        self.assertEqual(b'false', false_result.content)


class PropertyMergeViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.cycle = cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.property_state_factory.get_property_state(
            address_line_1='1 property state',
            pm_property_id='5766973'  # this allows the Property to be targetted for PM meter additions
        )
        self.property_1 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=self.property_1, cycle=self.cycle, state=self.state_1
        )

        self.state_2 = self.property_state_factory.get_property_state(address_line_1='2 property state')
        self.property_2 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=self.property_2, cycle=self.cycle, state=self.state_2
        )

        self.import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

    def test_properties_merge_without_losing_meters_1st_has_meters(self):
        # Assign meters to the first Property
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        self.assertEqual(PropertyView.objects.first().property.meters.count(), 1)
        self.assertEqual(PropertyView.objects.first().property.meters.first().meter_readings.count(), 2)

    def test_properties_merge_without_losing_meters_2nd_has_meters(self):
        # Assign Meters to the second Property
        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename
        import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        self.assertEqual(PropertyView.objects.first().property.meters.count(), 1)
        self.assertEqual(PropertyView.objects.first().property.meters.first().meter_readings.count(), 2)

    def test_properties_merge_without_losing_meters_from_different_sources_nonoverlapping(self):
        # For first Property, PM Meters containing 2 readings for each Electricty and Natural Gas for property_1
        # This file has multiple tabs
        pm_filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + pm_filename
        pm_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=pm_filename,
            file=SimpleUploadedFile(name=pm_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
        )
        pm_import_url = reverse("api:v2:import_files-save-raw-data", args=[pm_import_file.id])
        pm_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(pm_import_url, pm_import_post_params)

        # For second Property, add GreenButton Meters containing 2 readings for Electricity only
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[gb_import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge PropertyStates
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        # The Property of the (only) -View has all of the Meters now.
        meters = PropertyView.objects.first().property.meters

        self.assertEqual(meters.count(), 3)
        self.assertEqual(meters.get(type=Meter.ELECTRICITY_GRID, source=Meter.GREENBUTTON).meter_readings.count(), 2)
        self.assertEqual(meters.get(type=Meter.ELECTRICITY_GRID, source=Meter.PORTFOLIO_MANAGER).meter_readings.count(), 2)
        self.assertEqual(meters.get(type=Meter.NATURAL_GAS).meter_readings.count(), 2)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 3)
        self.assertEqual(MeterReading.objects.count(), 6)

    def test_properties_merge_without_losing_meters_when_some_meters_from_same_source_are_overlapping(self):
        # For first Property, add GreenButton Meters containing 2 readings for Electricity only
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[gb_import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # For second Property, add GreenButton Meters containing 2 Electricitiy readings: 1 overlapping
        gb_overlapping_filename = "example-GreenButton-data-1-overlapping.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_overlapping_filename
        gb_overlapping_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=gb_overlapping_filename,
            file=SimpleUploadedFile(name=gb_overlapping_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_2.id}  # this is how target property is specified
        )
        gb_overlapping_import_url = reverse("api:v2:import_files-save-raw-data", args=[gb_overlapping_import_file.id])
        gb_overlapping_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_overlapping_import_url, gb_overlapping_import_post_params)

        # Check that there are 2 overlapping readings (that are separate for now) out of 4.
        self.assertEqual(MeterReading.objects.count(), 4)
        tz_obj = timezone(TIME_ZONE)
        start_time_match = make_aware(datetime(2011, 3, 5, 21, 15, 0), timezone=tz_obj)
        end_time_match = make_aware(datetime(2011, 3, 5, 21, 30, 0), timezone=tz_obj)
        same_time_windows = MeterReading.objects.filter(
            start_time=start_time_match,
            end_time=end_time_match
        )
        self.assertEqual(same_time_windows.count(), 2)

        # Capture the overlapping reading of property_1, and ensure it's different from property_2's
        priority_property_id = self.property_1.meters.first().id
        property_1_reading = same_time_windows.get(meter_id=priority_property_id).reading
        property_2_reading = same_time_windows.exclude(meter_id=priority_property_id).get().reading
        self.assertNotEqual(property_1_reading, property_2_reading)

        # Merge PropertyStates
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should only be one PropertyView
        self.assertEqual(PropertyView.objects.count(), 1)

        # The Property of the (only) -View has all of the Meters now.
        meters = PropertyView.objects.first().property.meters
        self.assertEqual(meters.count(), 1)
        self.assertEqual(meters.first().meter_readings.count(), 3)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 1)
        self.assertEqual(MeterReading.objects.count(), 3)

        # Check that the resulting reading used belonged to property_1
        merged_reading = MeterReading.objects.filter(
            start_time=start_time_match,
            end_time=end_time_match
        )
        self.assertEqual(merged_reading.count(), 1)
        self.assertEqual(merged_reading.first().reading, property_1_reading)

        # Overlapping reading that wasn't prioritized should not exist
        self.assertFalse(MeterReading.objects.filter(reading=property_2_reading).exists())

    def test_properties_merge_combining_bsync_and_pm_sources(self):
        # For first Property, PM Meters containing 2 readings for each Electricty and Natural Gas for property_1
        # This file has multiple tabs
        pm_filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + pm_filename
        pm_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=pm_filename,
            file=SimpleUploadedFile(name=pm_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
        )
        pm_import_url = reverse("api:v2:import_files-save-raw-data", args=[pm_import_file.id])
        pm_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(pm_import_url, pm_import_post_params)

        # For second Property, add BuildingSync file containing 6 meters
        bs_filename = "buildingsync_v2_0_bricr_workflow.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/../building_sync/tests/data/" + bs_filename
        bs_file = open(filepath, 'rb')
        uploaded_file = SimpleUploadedFile(bs_file.name, bs_file.read())
        bs_buildingfile = BuildingFile.objects.create(
            file=uploaded_file,
            filename=bs_filename,
            file_type=BuildingFile.BUILDINGSYNC,
        )
        p_status, bs_property_state, _, _ = bs_buildingfile.process(self.org.pk, self.cycle)
        self.assertTrue(p_status)

        # Merge PropertyStates
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_1.pk, bs_property_state.pk]  # priority given to bs_property_state
        })
        self.client.post(url, post_params, content_type='application/json')

        # There should only be _two_ PropertyViews (our setUp creates an additional one that's not merged)
        self.assertEqual(PropertyView.objects.count(), 1)

        # The Property of the *newest* -View has all of the Meters now.
        meters = PropertyView.objects.last().property.meters

        self.assertEqual(meters.count(), 8)  # 2 from PM, 6 from BS
        self.assertEqual(meters.filter(type=Meter.ELECTRICITY_GRID, source=Meter.BUILDINGSYNC).count(), 3)
        self.assertEqual(meters.filter(type=Meter.NATURAL_GAS, source=Meter.BUILDINGSYNC).count(), 3)
        self.assertEqual(meters.filter(type=Meter.ELECTRICITY_GRID, source=Meter.PORTFOLIO_MANAGER).count(), 1)
        self.assertEqual(meters.filter(type=Meter.NATURAL_GAS, source=Meter.PORTFOLIO_MANAGER).count(), 1)

        # Old meters deleted, so only merged meters exist
        self.assertEqual(Meter.objects.count(), 8)
        self.assertEqual(MeterReading.objects.count(), 76)


class PropertyUnmergeViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        self.cycle = cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.property_state_factory.get_property_state(
            address_line_1='1 property state',
            pm_property_id='5766973'  # this allows the Property to be targetted for PM meter additions
        )
        self.property_1 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=self.property_1, cycle=self.cycle, state=self.state_1
        )

        self.state_2 = self.property_state_factory.get_property_state(address_line_1='2 property state')
        self.property_2 = self.property_factory.get_property()
        PropertyView.objects.create(
            property=self.property_2, cycle=self.cycle, state=self.state_2
        )

        self.import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        # Give 2 meters to one of the properties
        gb_filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + gb_filename
        gb_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="GreenButton",
            uploaded_filename=gb_filename,
            file=SimpleUploadedFile(name=gb_filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id}  # this is how target property is specified
        )
        gb_import_url = reverse("api:v2:import_files-save-raw-data", args=[gb_import_file.id])
        gb_import_post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(gb_import_url, gb_import_post_params)

        # Merge the properties
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

    def test_unmerging_two_properties_with_meters_gives_meters_to_both_of_the_resulting_records(self):
        # Unmerge the properties
        view_id = PropertyView.objects.first().id  # There's only one PropertyView
        url = reverse('api:v2:properties-unmerge', args=[view_id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        # Verify 2 -Views now exist
        self.assertEqual(PropertyView.objects.count(), 2)

        # Check that meters and readings of each -View exists and verify they are identical.
        reading_sets = []
        for view in PropertyView.objects.all():
            self.assertEqual(view.property.meters.count(), 1)
            self.assertEqual(view.property.meters.first().meter_readings.count(), 2)
            reading_sets.append([
                {
                    'start_time': reading.start_time,
                    'end_time': reading.end_time,
                    'reading': reading.reading,
                    'source_unit': reading.source_unit,
                    'conversion_factor': reading.conversion_factor,
                }
                for reading
                in view.property.meters.first().meter_readings.all().order_by('start_time')
            ])

        self.assertEqual(reading_sets[0], reading_sets[1])
