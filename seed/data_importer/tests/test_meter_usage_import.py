# !/usr/bin/env python
# encoding: utf-8

import json
import os

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import TestCase
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)

from pytz import timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tasks import match_buildings
from seed.landing.models import SEEDUser as User
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    DATA_STATE_DELETE,
    Meter,
    MeterReading,
    Property,
    PropertyState,
    PropertyView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class MeterUsageImportTest(TestCase):
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

        self.import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        # This file has multiple tabs
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        self.tz_obj = timezone(TIME_ZONE)

    def test_import_meter_usage_file_base_case(self):
        """
        Expect to have 4 meters - 2 for each property - 1 for gas and 1 for electricity.
        Each meter will have 2 readings, for a total of 8 readings.
        These come from 8 meter usage rows in the .xlsx file - 1 per reading.
        """
        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 2)

        meter_1 = refreshed_property_1.meters.get(type=Meter.ELECTRICITY_GRID)
        self.assertEqual(meter_1.source, Meter.PORTFOLIO_MANAGER)
        self.assertEqual(meter_1.source_id, '5766973-0')
        self.assertEqual(meter_1.is_virtual, False)
        self.assertEqual(meter_1.meter_readings.all().count(), 2)

        meter_reading_10, meter_reading_11 = list(meter_1.meter_readings.order_by('start_time').all())

        self.assertEqual(meter_reading_10.start_time, make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_10.end_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_10.reading, 597478.9)
        self.assertEqual(meter_reading_10.source_unit, "kBtu (thousand Btu)")  # spot check
        self.assertEqual(meter_reading_10.conversion_factor, 1)  # spot check

        self.assertEqual(meter_reading_11.start_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_11.end_time, make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_11.reading, 548603.7)

        meter_2 = refreshed_property_1.meters.get(type=Meter.NATURAL_GAS)
        self.assertEqual(meter_2.source, Meter.PORTFOLIO_MANAGER)
        self.assertEqual(meter_2.source_id, '5766973-1')
        self.assertEqual(meter_2.meter_readings.all().count(), 2)

        meter_reading_20, meter_reading_21 = list(meter_2.meter_readings.order_by('start_time').all())

        self.assertEqual(meter_reading_20.start_time, make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_20.end_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_20.reading, 576000.2)

        self.assertEqual(meter_reading_21.start_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_21.end_time, make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_21.reading, 488000.1)

        refreshed_property_2 = Property.objects.get(pk=self.property_2.id)
        self.assertEqual(refreshed_property_2.meters.all().count(), 2)

        meter_3 = refreshed_property_2.meters.get(type=Meter.ELECTRICITY_GRID)
        self.assertEqual(meter_3.source, Meter.PORTFOLIO_MANAGER)
        self.assertEqual(meter_3.source_id, '5766975-0')
        self.assertEqual(meter_3.meter_readings.all().count(), 2)

        meter_reading_30, meter_reading_40 = list(meter_3.meter_readings.order_by('start_time').all())

        self.assertEqual(meter_reading_30.start_time, make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_30.end_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_30.reading, 154572.2)
        self.assertEqual(meter_reading_30.source_unit, "kBtu (thousand Btu)")  # spot check
        self.assertEqual(meter_reading_30.conversion_factor, 1)  # spot check

        self.assertEqual(meter_reading_40.start_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_40.end_time, make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_40.reading, 141437.5)

        meter_4 = refreshed_property_2.meters.get(type=Meter.NATURAL_GAS)
        self.assertEqual(meter_4.source, Meter.PORTFOLIO_MANAGER)
        self.assertEqual(meter_4.source_id, '5766975-1')
        self.assertEqual(meter_4.meter_readings.all().count(), 2)

        meter_reading_40, meter_reading_41 = list(meter_4.meter_readings.order_by('start_time').all())

        self.assertEqual(meter_reading_40.start_time, make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_40.end_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_40.reading, 299915)

        self.assertEqual(meter_reading_41.start_time, make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_41.end_time, make_aware(datetime(2016, 3, 1, 0, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_41.reading, 496310.9)

        # file should be disassociated from cycle too
        refreshed_import_file = ImportFile.objects.get(pk=self.import_file.id)
        self.assertEqual(refreshed_import_file.cycle_id, None)

    def test_import_meter_usage_file_ignores_unknown_types_or_units(self):
        """
        Expect to have 3 meters.
        The first meter belongs to the first property and should have 2 readings.
        The second meter belongs to the second property and should have 1 reading.
        The last meter belongs to the second property and should have 1 reading.

        These come from 8 meter usage rows in the .xlsx file (1 per reading)
        where 4 of them have either an invalid type or unit.
        """
        filename = "example-pm-monthly-meter-usage-with-unknown-types-and-units.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        import_file_with_invalids = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse("api:v2:import_files-save-raw-data", args=[import_file_with_invalids.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        self.assertEqual(3, Meter.objects.count())
        self.assertEqual(4, MeterReading.objects.count())

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 1)

        meter_1 = refreshed_property_1.meters.first()
        self.assertEqual(meter_1.meter_readings.all().count(), 2)

        refreshed_property_2 = Property.objects.get(pk=self.property_2.id)
        self.assertEqual(refreshed_property_2.meters.all().count(), 2)

        meter_2 = refreshed_property_2.meters.get(type=Meter.ELECTRICITY_GRID)
        self.assertEqual(meter_2.meter_readings.all().count(), 1)

        meter_3 = refreshed_property_2.meters.get(type=Meter.NATURAL_GAS)
        self.assertEqual(meter_3.meter_readings.all().count(), 1)

    def test_import_meter_usage_file_including_2_cost_meters(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_meter_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse("api:v2:import_files-save-raw-data", args=[cost_meter_import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        cost_meters = Meter.objects.filter(type=Meter.COST)

        self.assertEqual(2, cost_meters.count())

        electric_cost_meter = cost_meters.get(source_id='5766973-0')
        gas_cost_meter = cost_meters.get(source_id='5766973-1')

        self.assertEqual(2, electric_cost_meter.meter_readings.count())
        self.assertEqual(2, gas_cost_meter.meter_readings.count())

        electric_reading_values = electric_cost_meter.meter_readings.values_list('reading', flat=True)
        self.assertCountEqual([100, 200], electric_reading_values)

        gas_reading_values = gas_cost_meter.meter_readings.values_list('reading', flat=True)
        self.assertCountEqual([300, 400], gas_reading_values)

    def test_existing_meter_is_found_and_used_if_import_file_should_reference_it(self):
        property = Property.objects.get(pk=self.property_1.id)

        # Create a meter with the same details of one meter in the import file
        unsaved_meter = Meter(
            property=property,
            source=Meter.PORTFOLIO_MANAGER,
            source_id='5766973-0',
            type=Meter.ELECTRICITY_GRID,
        )
        unsaved_meter.save()
        existing_meter = Meter.objects.get(pk=unsaved_meter.id)

        # Create a reading with a different date from those in the import file
        unsaved_meter_reading = MeterReading(
            meter=existing_meter,
            start_time=make_aware(datetime(2018, 1, 1, 0, 0, 0), timezone=self.tz_obj),
            end_time=make_aware(datetime(2018, 2, 1, 0, 0, 0), timezone=self.tz_obj),
            reading=12345,
            conversion_factor=1.0
        )
        unsaved_meter_reading.save()
        existing_meter_reading = MeterReading.objects.get(reading=12345)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 2)

        refreshed_meter = refreshed_property_1.meters.get(type=Meter.ELECTRICITY_GRID)

        meter_reading_10, meter_reading_11, meter_reading_12 = list(refreshed_meter.meter_readings.order_by('start_time').all())
        self.assertEqual(meter_reading_10.reading, 597478.9)
        self.assertEqual(meter_reading_11.reading, 548603.7)

        # Sanity check to be sure, nothing was changed with existing meter reading
        self.assertEqual(meter_reading_12, existing_meter_reading)

    def test_existing_meter_reading_has_reading_source_unit_and_conversion_factor_updated_if_import_file_references_previous_entry(self):
        property = Property.objects.get(pk=self.property_1.id)

        # Create a meter with the same details of one meter in the import file
        unsaved_meter = Meter(
            property=property,
            source=Meter.PORTFOLIO_MANAGER,
            source_id='5766973-0',
            type=Meter.ELECTRICITY_GRID,
        )
        unsaved_meter.save()
        existing_meter = Meter.objects.get(pk=unsaved_meter.id)

        # Create a reading with the same date as one from the import file but different reading
        start_time = make_aware(datetime(2016, 1, 1, 0, 0, 0), timezone=self.tz_obj)
        end_time = make_aware(datetime(2016, 2, 1, 0, 0, 0), timezone=self.tz_obj)

        unsaved_meter_reading = MeterReading(
            meter=existing_meter,
            start_time=start_time,
            end_time=end_time,
            reading=12345,
            source_unit="GJ",
            conversion_factor=947.82
        )
        unsaved_meter_reading.save()

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        # Just as in the first test, 8 meter readings should exist
        self.assertEqual(MeterReading.objects.all().count(), 8)

        refreshed_property = Property.objects.get(pk=self.property_1.id)
        refreshed_meter = refreshed_property.meters.get(type=Meter.ELECTRICITY_GRID)
        meter_reading = refreshed_meter.meter_readings.get(start_time=start_time)

        self.assertEqual(meter_reading.end_time, end_time)
        self.assertEqual(meter_reading.reading, 597478.9)
        self.assertEqual(meter_reading.source_unit, "kBtu (thousand Btu)")
        self.assertEqual(meter_reading.conversion_factor, 1)

    def test_property_existing_in_multiple_cycles_can_have_meters_and_readings_associated_to_it(self):
        property_details = FakePropertyStateFactory(organization=self.org).get_details()
        property_details['organization_id'] = self.org.id

        # new state to be associated to new cycle using the same pm_property_id as state in old cycle
        property_details['pm_property_id'] = self.state_1.pm_property_id
        state = PropertyState(**property_details)
        state.save()
        new_property_state = PropertyState.objects.get(pk=state.id)

        new_cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        new_cycle = new_cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        # new state and cycle associated to old property
        PropertyView.objects.create(property=self.property_1, cycle=new_cycle, state=new_property_state)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 2)

    def test_meters_and_readings_are_associated_to_every_record_across_all_cycles_with_a_given_pm_property_id(self):
        # new, in-cycle state NOT associated to existing record but has same PM Property ID
        property_details_1 = FakePropertyStateFactory(organization=self.org).get_details()
        property_details_1['organization_id'] = self.org.id
        property_details_1['pm_property_id'] = self.state_1.pm_property_id
        property_details_1['custom_id_1'] = "values that forces non-match"
        new_property_1 = PropertyState(**property_details_1)
        new_property_1.save()

        property_3 = self.property_factory.get_property()
        PropertyView.objects.create(property=property_3, cycle=self.cycle, state=new_property_1)

        # new, out-cycle state NOT associated to existing record but has same PM Property ID
        property_details_2 = FakePropertyStateFactory(organization=self.org).get_details()
        property_details_2['organization_id'] = self.org.id
        property_details_2['pm_property_id'] = self.state_1.pm_property_id
        property_details_2['custom_id_1'] = "second value that forces non-match"
        new_property_2 = PropertyState(**property_details_2)
        new_property_2.save()

        new_cycle = self.cycle_factory.get_cycle(start=datetime(2011, 10, 10, tzinfo=get_current_timezone()))
        property_4 = self.property_factory.get_property()
        PropertyView.objects.create(property=property_4, cycle=new_cycle, state=new_property_2)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 2)

        refreshed_property_3 = Property.objects.get(pk=property_3.id)
        self.assertEqual(refreshed_property_3.meters.all().count(), 2)

        refreshed_property_4 = Property.objects.get(pk=property_4.id)
        self.assertEqual(refreshed_property_4.meters.all().count(), 2)

    def test_pm_property_id_existing_across_two_different_orgs_wont_lead_to_misassociated_meters(self):
        new_org, _, _ = create_organization(self.user)

        property_details = FakePropertyStateFactory(organization=new_org).get_details()
        property_details['organization_id'] = new_org.id

        # new state to be associated to property of different organization but has the same pm_property_id
        property_details['pm_property_id'] = self.state_1.pm_property_id
        state = PropertyState(**property_details)
        state.save()
        new_property_state = PropertyState.objects.get(pk=state.id)

        new_cycle_factory = FakeCycleFactory(organization=new_org, user=self.user)
        new_cycle = new_cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        new_property = self.property_factory.get_property()

        PropertyView.objects.create(property=new_property, cycle=new_cycle, state=new_property_state)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        # self.property_1 is associated to self.org, so according to post request, it should have 2 meters
        refreshed_property_1 = Property.objects.get(pk=self.property_1.id, organization_id__exact=self.org.pk)
        self.assertEqual(refreshed_property_1.meters.all().count(), 2)

        refreshed_new_property = Property.objects.get(pk=new_property.id)
        self.assertEqual(refreshed_new_property.meters.count(), 0)

    def test_the_response_contains_expected_and_actual_reading_counts_single_cycle(self):
        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        result = json.loads(response.content)

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
        ]

        self.assertCountEqual(result['message'], expectation)

    def test_the_response_contains_expected_and_actual_reading_counts_across_cycles_for_linked_properties(self):
        property_details = FakePropertyStateFactory(organization=self.org).get_details()
        property_details['organization_id'] = self.org.id

        # new state will be linked to existing record and has same PM Property ID
        property_details['pm_property_id'] = self.state_1.pm_property_id
        state = PropertyState(**property_details)
        state.save()

        new_property_state = PropertyState.objects.get(pk=state.id)
        new_cycle = self.cycle_factory.get_cycle(start=datetime(2011, 10, 10, tzinfo=get_current_timezone()))

        PropertyView.objects.create(property=self.property_1, cycle=new_cycle, state=new_property_state)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        result = json.loads(response.content)

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name + ", " + new_cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name + ", " + new_cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
        ]

        self.assertCountEqual(result['message'], expectation)

    def test_the_response_contains_expected_and_actual_reading_counts_by_property_id_even_in_the_same_cycle(self):
        property_details = FakePropertyStateFactory(organization=self.org).get_details()
        property_details['organization_id'] = self.org.id

        # Create new state NOT associated to existing record but has same PM Property ID
        property_details['pm_property_id'] = self.state_1.pm_property_id
        property_details['custom_id_1'] = "values that forces non-match"
        state = PropertyState(**property_details)
        state.save()
        new_property_state = PropertyState.objects.get(pk=state.id)

        # new state in cycle associated to old property
        property_3 = self.property_factory.get_property()
        PropertyView.objects.create(property=property_3, cycle=self.cycle, state=new_property_state)

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        result = json.loads(response.content)

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": property_3.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": property_3.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
        ]

        self.assertCountEqual(result['message'], expectation)

    def test_the_response_contains_expected_and_actual_reading_counts_for_pm_ids_with_costs(self):
        filename = "example-pm-monthly-meter-usage-2-cost-meters.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        cost_meter_import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse("api:v2:import_files-save-raw-data", args=[cost_meter_import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        result = json.loads(response.content)

        expectation = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Cost",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Cost",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
            },
        ]

        self.assertCountEqual(result['message'], expectation)

    def test_error_noted_in_response_if_meter_has_overlapping_readings(self):
        """
        If a meter has overlapping readings, the process of upserting a reading
        will encounter the issue of not knowing which reading should take
        precedence over the other.

        In this case, neither the meter (if applicable) nor any of its readings
        are created.
        """
        dup_import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
        dup_filename = "example-pm-monthly-meter-usage-1-dup.xlsx"
        dup_filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + dup_filename

        dup_file = ImportFile.objects.create(
            import_record=dup_import_record,
            source_type="PM Meter Usage",
            uploaded_filename=dup_filename,
            file=SimpleUploadedFile(name=dup_filename, content=open(dup_filepath, 'rb').read()),
            cycle=self.cycle
        )

        url = reverse("api:v2:import_files-save-raw-data", args=[dup_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        total_meters_count = Meter.objects.count()

        result_summary = json.loads(response.content)

        expected_import_summary = [
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-0",
                "type": "Electric - Grid",
                "incoming": 2,
                "successfully_imported": 2,
                "errors": "",
            },
            {
                "property_id": self.property_1.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766973",
                "source_id": "5766973-1",
                "type": "Natural Gas",
                "incoming": 2,
                "successfully_imported": 2,
                "errors": "",
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-0",
                "type": "Electric - Grid",
                "incoming": 4,
                "successfully_imported": 0,
                "errors": "Overlapping readings.",
            },
            {
                "property_id": self.property_2.id,
                "cycles": self.cycle.name,
                "pm_property_id": "5766975",
                "source_id": "5766975-1",
                "type": "Natural Gas",
                "incoming": 4,
                "successfully_imported": 0,
                "errors": "Overlapping readings.",
            },
        ]

        self.assertCountEqual(result_summary['message'], expected_import_summary)
        self.assertEqual(total_meters_count, 2)


class MeterUsageImportAdjustedScenarioTest(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record, self.cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_property_states_not_associated_to_properties_are_not_targetted_on_meter_import(self):
        # Create three pm_property_id = 5766973 properties that are exact duplicates
        base_details = {
            'address_line_1': '123 Match Street',
            'pm_property_id': '5766973',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # Create 1 property with a duplicate in the first ImportFile
        self.property_state_factory.get_property_state(**base_details)
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        import_record_2, import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle
        )

        # Create another duplicate property coming from second ImportFile
        base_details['import_file_id'] = import_file_2.id
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        match_buildings(import_file_2.id)

        # Import the PM Meters
        filename = "example-pm-monthly-meter-usage.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        pm_meter_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="PM Meter Usage",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle
        )

        # Check that meters pre-upload confirmation runs without problems
        confirmation_url = reverse('api:v2:meters-parsed-meters-confirmation')
        confirmation_post_params = json.dumps({
            'file_id': pm_meter_file.id,
            'organization_id': self.org.pk,
        })
        self.client.post(confirmation_url, confirmation_post_params, content_type="application/json")

        url = reverse("api:v2:import_files-save-raw-data", args=[pm_meter_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        # Check that Meters have been uploaded successfully (there's only 2 since only pm_property_id 5766973 exists)
        self.assertEqual(Meter.objects.count(), 2)

        # Ensure that no meters were associated to the duplicate PropertyStates via PropertyViews
        delete_flagged_ids = PropertyState.objects.filter(data_state=DATA_STATE_DELETE).values_list('id', flat=True)
        for meter in Meter.objects.all():
            self.assertEqual(meter.property.views.filter(state_id__in=delete_flagged_ids).count(), 0)
