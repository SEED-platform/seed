# !/usr/bin/env python
# encoding: utf-8

import json
import os

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import (
    get_current_timezone,
    make_aware,  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
)

from pytz import timezone

from quantityfield import ureg

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.models import (
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
from seed.utils.organizations import create_organization


class GreenButtonImportTest(TestCase):
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
        state_1 = PropertyState(**property_details)
        state_1.save()
        self.state_1 = PropertyState.objects.get(pk=state_1.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_1 = self.property_factory.get_property()

        self.property_view_1 = PropertyView.objects.create(property=self.property_1, cycle=self.cycle, state=self.state_1)

        import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)

        filename = "example-GreenButton-data.xml"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        self.import_file = ImportFile.objects.create(
            import_record=import_record,
            source_type="GreenButton",
            uploaded_filename=filename,
            file=SimpleUploadedFile(name=filename, content=open(filepath, 'rb').read()),
            cycle=self.cycle,
            matching_results_data={"property_id": self.property_1.id} # TODO: subject to change
        )

        self.tz_obj = timezone(TIME_ZONE)

    def test_green_button_import_base_case(self):
        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        refreshed_property_1 = Property.objects.get(pk=self.property_1.id)
        self.assertEqual(refreshed_property_1.meters.all().count(), 1)

        meter_1 = refreshed_property_1.meters.get(type=Meter.ELECTRICITY)
        self.assertEqual(meter_1.source, Meter.GREENBUTTON)
        self.assertEqual(meter_1.source_id, 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1')
        self.assertEqual(meter_1.is_virtual, False)
        self.assertEqual(meter_1.meter_readings.all().count(), 2)

        meter_reading_10, meter_reading_11 = list(meter_1.meter_readings.order_by('start_time').all())

        self.assertEqual(meter_reading_10.start_time, make_aware(datetime(2011, 3, 5, 21, 0, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_10.end_time, make_aware(datetime(2011, 3, 5, 21, 15, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_10.reading, 1790 * 3.412 / 1000 * ureg('kBtu'))
        self.assertEqual(meter_reading_10.source_unit, "kWh")
        self.assertEqual(meter_reading_10.conversion_factor, 3.412)

        self.assertEqual(meter_reading_11.start_time, make_aware(datetime(2011, 3, 5, 21, 15, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_11.end_time, make_aware(datetime(2011, 3, 5, 21, 30, 0), timezone=self.tz_obj))
        self.assertEqual(meter_reading_11.reading, 1791 * 3.412 / 1000 * ureg('kBtu'))
        self.assertEqual(meter_reading_11.source_unit, "kWh")
        self.assertEqual(meter_reading_11.conversion_factor, 3.412)

    def test_existing_meter_is_found_and_used_if_import_file_should_reference_it(self):
        property = Property.objects.get(pk=self.property_1.id)

        # Create a meter with the same details of the meter in the import file
        unsaved_meter = Meter(
            property=property,
            source=Meter.GREENBUTTON,
            source_id='User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
            type=Meter.ELECTRICITY,
        )
        unsaved_meter.save()
        existing_meter = Meter.objects.get(pk=unsaved_meter.id)

        # Create a reading with a different date from those in the import file
        unsaved_meter_reading = MeterReading(
            meter=existing_meter,
            start_time=make_aware(datetime(2018, 1, 1, 0, 0, 0), timezone=self.tz_obj),
            end_time=make_aware(datetime(2018, 2, 1, 0, 0, 0), timezone=self.tz_obj),
            reading=12345,
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
        self.assertEqual(refreshed_property_1.meters.all().count(), 1)

        refreshed_meter = refreshed_property_1.meters.get(type=Meter.ELECTRICITY)

        meter_reading_10, meter_reading_11, meter_reading_12 = list(refreshed_meter.meter_readings.order_by('start_time').all())
        self.assertEqual(meter_reading_10.reading, 1790 * 3.412 / 1000 * ureg('kBtu'))
        self.assertEqual(meter_reading_11.reading, 1791 * 3.412 / 1000 * ureg('kBtu'))

        # Sanity check to be sure, nothing was changed with existing meter reading
        self.assertEqual(meter_reading_12, existing_meter_reading)

    def test_existing_meter_reading_has_reading_source_unit_and_conversion_factor_updated_if_import_file_references_previous_entry(self):
        property = Property.objects.get(pk=self.property_1.id)

        # Create a meter with the same details of one meter in the import file
        unsaved_meter = Meter(
            property=property,
            source=Meter.GREENBUTTON,
            source_id='User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
            type=Meter.ELECTRICITY,
        )
        unsaved_meter.save()
        existing_meter = Meter.objects.get(pk=unsaved_meter.id)

        # Create a reading with the same date as one from the import file but different reading
        start_time = make_aware(datetime(2011, 3, 5, 21, 0, 0), timezone=self.tz_obj)
        end_time = make_aware(datetime(2011, 3, 5, 21, 15, 0), timezone=self.tz_obj)

        unsaved_meter_reading = MeterReading(
            meter=existing_meter,
            start_time=start_time,
            end_time=end_time,
            reading=1000,
            source_unit="GJ",
            conversion_factor=947.817
        )
        unsaved_meter_reading.save()

        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        self.client.post(url, post_params)

        # Just as in the first test, 2 meter readings should exist
        self.assertEqual(MeterReading.objects.all().count(), 2)

        refreshed_property = Property.objects.get(pk=self.property_1.id)
        refreshed_meter = refreshed_property.meters.get(type=Meter.ELECTRICITY)
        meter_reading = refreshed_meter.meter_readings.get(start_time=start_time)

        self.assertEqual(meter_reading.end_time, end_time)
        self.assertEqual(meter_reading.reading, 1790 * 3.412 / 1000 * ureg('kBtu'))
        self.assertEqual(meter_reading.source_unit, "kWh")
        self.assertEqual(meter_reading.conversion_factor, 3.412)

    def test_the_response_contains_expected_and_actual_reading_counts_for_pm_ids(self):
        url = reverse("api:v2:import_files-save-raw-data", args=[self.import_file.id])
        post_params = {
            'cycle_id': self.cycle.pk,
            'organization_id': self.org.pk,
        }
        response = self.client.post(url, post_params)

        result = json.loads(response.content)

        expectation = [
            {
                "source_id": "409483",
                "incoming": 2,
                "successfully_imported": 2,
            },
        ]

        self.assertEqual(result['message'], expectation)

    # there should be an error if there exists the same time interval within the same import file
    #   this needs to be checked before the SQL queries are sent since...

    # Each file will probably be the data for only one meter
    # but can expect it to have many readings, so...

    # We'll probably want to be able to batch the by some, say 1000, meter_readings vs
    # batching each meter to its own job

    # def test_error_noted_in_response_if_meter_has_overlapping_readings(self):
    #     """
    #     If a meter has overlapping readings, the process of upserting a reading
    #     will encounter the issue of not knowing which reading should take
    #     precedence over the other.
    #
    #     In this case, neither the meter (if applicable) nor any of its readings
    #     are created.
    #     """
    #     dup_import_record = ImportRecord.objects.create(owner=self.user, last_modified_by=self.user, super_organization=self.org)
    #     dup_filename = "example-pm-monthly-meter-usage-1-dup.xlsx"
    #     dup_filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + dup_filename
    #
    #     dup_file = ImportFile.objects.create(
    #         import_record=dup_import_record,
    #         source_type="PM Meter Usage",
    #         uploaded_filename=dup_filename,
    #         file=SimpleUploadedFile(name=dup_filename, content=open(dup_filepath, 'rb').read()),
    #         cycle=self.cycle
    #     )
    #
    #     url = reverse("api:v2:import_files-save-raw-data", args=[dup_file.id])
    #     post_params = {
    #         'cycle_id': self.cycle.pk,
    #         'organization_id': self.org.pk,
    #     }
    #     response = self.client.post(url, post_params)
    #
    #     total_meters_count = Meter.objects.count()
    #
    #     result_summary = json.loads(response.content)
    #
    #     expected_import_summary = [
    #         {
    #             "portfolio_manager_id": "5766973",
    #             "incoming": 4,
    #             "successfully_imported": 4,
    #             "errors": "",
    #         },
    #         {
    #             "portfolio_manager_id": "5766975",
    #             "incoming": 8,
    #             "successfully_imported": 0,
    #             "errors": "Overlapping readings.",
    #         },
    #     ]
    #
    #     self.assertEqual(result_summary['message'], expected_import_summary)
    #     self.assertEqual(total_meters_count, 2)
