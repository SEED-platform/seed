"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.urls import reverse
from django.utils.timezone import make_aware  # make_aware is used because inconsistencies exist in creating datetime with tzinfo

from seed.data_importer.tasks import _save_sensor_readings_task
from seed.lib.progress_data.progress_data import ProgressData
from seed.models.sensors import DataLogger, Sensor, SensorReading
from seed.test_helpers.fake import FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase


class PropertySensorViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_view_1 = property_view_factory.get_property_view()
        self.property_1 = self.property_view_1.property

        self.property_view_2 = property_view_factory.get_property_view()
        self.property_2 = self.property_view_2.property

    def test_create_data_loggers_permissions(self):
        url = reverse("api:v3:data_logger-list") + "?property_view_id=" + str(self.property_view_1.id)
        data = {"display_name": "boo", "location_description": "ah", "identifier": "me", "org_id": self.org.pk}

        # root users can create data logger in root
        self.login_as_root_member()
        result = self.client.post(url, json.dumps(data), content_type="application/json")
        assert result.status_code == 200

        # child user cannot
        self.login_as_child_member()
        data["display_name"] = "lol"
        result = self.client.post(url, json.dumps(data), content_type="application/json")
        assert result.status_code == 404

    def test_data_loggers_list_permissions(self):
        url = reverse("api:v3:data_logger-list")
        data = {"property_view_id": self.property_view_1.id, "org_id": self.org.pk}

        # root users can get data logger in root
        self.login_as_root_member()
        result = self.client.get(url, data)
        assert result.status_code == 200

        # child user cannot
        self.login_as_child_member()
        result = self.client.get(url, data)
        assert result.status_code == 404

    def test_data_loggers_delete_permissions(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")

        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl.id})
        url += f"?organization_id={self.org.pk}"

        # child user cannot
        self.login_as_child_member()
        result = self.client.delete(url)
        assert result.status_code == 404

        # root users can get data logger in root
        self.login_as_root_member()
        result = self.client.delete(url)
        assert result.status_code == 204

    def test_delete_sensor_permissions(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")

        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s.id})
        url += f"?organization_id={self.org.pk}"

        # child user cannot
        self.login_as_child_member()
        result = self.client.delete(url)
        assert result.status_code == 404

        # root users can get data logger in root
        self.login_as_root_member()
        result = self.client.delete(url)
        assert result.status_code == 204

    def test_update_data_logger_permissions(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")

        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack"})

        # child user cannot
        self.login_as_child_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 404

        # root users can
        self.login_as_root_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 200

    def test_update_sensor_permissions(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")

        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack"})

        # child user cannot
        self.login_as_child_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 404

        # root users can
        self.login_as_root_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 200

    def test_property_sensors_endpoint_returns_a_list_of_sensors_of_a_view(self):
        dl_a = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        Sensor.objects.create(data_logger=dl_a, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")
        Sensor.objects.create(data_logger=dl_a, display_name="s2", sensor_type="second", units="two", column_name="sensor 2")

        dl_b = DataLogger.objects.create(property_id=self.property_2.id, display_name="boo")
        Sensor.objects.create(data_logger=dl_b, display_name="s3", sensor_type="third", units="three", column_name="sensor 3")

        url = reverse("api:v3:property-sensors-list", kwargs={"property_pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"

        result = self.client.get(url)
        result_dict = json.loads(result.content)

        self.assertCountEqual([r["column_name"] for r in result_dict], ["sensor 1", "sensor 2"])

        url = reverse("api:v3:property-sensors-list", kwargs={"property_pk": self.property_view_2.id})
        url += f"?organization_id={self.org.pk}"

        result = self.client.get(url)
        result_dict = json.loads(result.content)

        self.assertCountEqual([r["column_name"] for r in result_dict], ["sensor 3"])

    def test_delete_sensor(self):
        dl_1 = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s1 = Sensor.objects.create(data_logger=dl_1, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")
        SensorReading.objects.create(
            reading=0.0, timestamp=str(datetime(2000, 1, 1, tzinfo=ZoneInfo(settings.TIME_ZONE))), sensor=s1, is_occupied=False
        )

        dl_2 = DataLogger.objects.create(property_id=self.property_1.id, display_name="bark")
        s2 = Sensor.objects.create(data_logger=dl_2, display_name="s2", sensor_type="second", units="two", column_name="sensor 2")
        SensorReading.objects.create(
            reading=0.0, timestamp=str(datetime(2000, 1, 1, tzinfo=ZoneInfo(settings.TIME_ZONE))), sensor=s2, is_occupied=False
        )

        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 2
        assert SensorReading.objects.count() == 2

        # Action
        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s1.id})
        url += f"?organization_id={self.org.pk}"
        result = self.client.delete(url, content_type="application/json")

        # Assertion
        assert result.status_code == 204
        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 1
        assert SensorReading.objects.count() == 1

    def test_property_sensor_usage_returns_sensor_readings(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s1 = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")
        s2 = Sensor.objects.create(data_logger=dl, display_name="s2", sensor_type="second", units="two", column_name="sensor 2")

        tz_obj = ZoneInfo(settings.TIME_ZONE)
        timestamps = [
            make_aware(datetime(year, month, day), timezone=tz_obj) for day in [10, 20] for month in [1, 2] for year in [2000, 2100]
        ]

        s1_reading = 0.0
        s2_reading = 10.0
        except_results = []
        for timestamp in timestamps:
            SensorReading.objects.create(reading=s1_reading, timestamp=timestamp, sensor=s1, is_occupied=False)
            SensorReading.objects.create(reading=s2_reading, timestamp=timestamp, sensor=s2, is_occupied=False)
            except_results.append(
                {
                    "timestamp": str(timestamp.replace(tzinfo=None)),
                    f"{s1.display_name} ({dl.display_name})": s1_reading,
                    f"{s2.display_name} ({dl.display_name})": s2_reading,
                }
            )
            s1_reading += 1
            s2_reading += 1

        url = reverse("api:v3:property-sensors-usage", kwargs={"property_pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "interval": "Exact",
                "excluded_sensor_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)
        self.assertCountEqual(result_dict["readings"], except_results)

        url = reverse("api:v3:property-sensors-usage", kwargs={"property_pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "interval": "Month",
                "excluded_sensor_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)

        self.assertCountEqual(
            result_dict["readings"],
            [
                {"month": "January 2000", "s1 (moo)": 2.0, "s2 (moo)": 12.0},
                {"month": "February 2000", "s1 (moo)": 4.0, "s2 (moo)": 14.0},
                {"month": "January 2100", "s1 (moo)": 3.0, "s2 (moo)": 13.0},
                {"month": "February 2100", "s1 (moo)": 5.0, "s2 (moo)": 15.0},
            ],
        )

        url = reverse("api:v3:property-sensors-usage", kwargs={"property_pk": self.property_view_1.id})
        url += f"?organization_id={self.org.pk}"
        post_params = json.dumps(
            {
                "interval": "Year",
                "excluded_sensor_ids": [],
            }
        )
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)

        self.assertCountEqual(
            result_dict["readings"],
            [
                {"year": 2000, "s1 (moo)": 3.0, "s2 (moo)": 13.0},
                {"year": 2100, "s1 (moo)": 4.0, "s2 (moo)": 14.0},
            ],
        )

    def test_save_sensor_readings_task_uses_local_schedule_boundaries(self):
        data_logger = DataLogger.objects.create(
            property_id=self.property_1.id,
            display_name="logger",
            is_occupied_data=[
                (datetime(2020, 1, 1, 8, 0, tzinfo=ZoneInfo(settings.TIME_ZONE)).isoformat(), True),
                (datetime(2020, 1, 1, 17, 0, tzinfo=ZoneInfo(settings.TIME_ZONE)).isoformat(), False),
            ],
        )
        sensor = Sensor.objects.create(
            data_logger=data_logger,
            display_name="sensor 1",
            sensor_type="first",
            units="one",
            column_name="sensor 1",
        )
        progress_data = ProgressData("save-sensor-readings-test", self.id())
        progress_data.total = 1
        progress_data.save()

        result = _save_sensor_readings_task(
            [
                ("2020-01-01 07:59:00", 1.0),
                ("2020-01-01 08:00:00", 2.0),
                ("2020-01-01 16:59:00", 3.0),
                ("2020-01-01 17:00:00", 4.0),
            ],
            data_logger.id,
            sensor.column_name,
            progress_data.key,
        )

        self.assertEqual(result[sensor.column_name]["count"], 4)
        self.assertEqual(
            list(SensorReading.objects.filter(sensor=sensor).order_by("timestamp").values_list("is_occupied", flat=True)),
            [False, True, True, False],
        )

    def test_delete_data_logger(self):
        dl_1 = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s1 = Sensor.objects.create(data_logger=dl_1, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")
        SensorReading.objects.create(
            reading=0.0, timestamp=str(datetime(2000, 1, 1, tzinfo=ZoneInfo(settings.TIME_ZONE))), sensor=s1, is_occupied=False
        )

        dl_2 = DataLogger.objects.create(property_id=self.property_1.id, display_name="bark")
        s2 = Sensor.objects.create(data_logger=dl_2, display_name="s2", sensor_type="second", units="two", column_name="sensor 2")
        SensorReading.objects.create(
            reading=0.0, timestamp=str(datetime(2000, 1, 1, tzinfo=ZoneInfo(settings.TIME_ZONE))), sensor=s2, is_occupied=False
        )

        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 2
        assert SensorReading.objects.count() == 2

        # Action
        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl_1.id})
        url += f"?organization_id={self.org.pk}"
        result = self.client.delete(url, content_type="application/json")

        # Assertion
        assert result.status_code == 204
        assert DataLogger.objects.count() == 1
        assert Sensor.objects.count() == 1
        assert SensorReading.objects.count() == 1

    def test_update_data_logger(self):
        # Set Up
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")

        # Action
        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack"})
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 200
        assert DataLogger.objects.first().display_name == "quack"

    def test_update_data_logger_duplicate_display_name(self):
        # Set Up
        DataLogger.objects.create(property_id=self.property_1.id, display_name="quack")
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")

        # Action
        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack"})
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 400

    def test_update_sensor(self):
        # Set Up
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")

        # Action
        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack"})
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 200
        assert Sensor.objects.first().display_name == "quack"

    def test_update_sensor_duplicate_display_name(self):
        # Set Up
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s1 = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")
        Sensor.objects.create(data_logger=dl, display_name="s2", sensor_type="first", units="one", column_name="sensor 2")

        # Action
        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s1.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "s2"})
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 400

    def test_update_and_delete_sensor_of_another_property(self):
        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        child_property_view = self.property_view_factory.get_property_view(child_property)
        child_dl = DataLogger.objects.create(property_id=child_property.id, display_name="child")
        child_sensor = Sensor.objects.create(data_logger=child_dl, display_name="s1", sensor_type="first", units="one", column_name="c 1")
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        s = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")

        def sensor_url(sensor):
            url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": child_property_view.pk, "pk": sensor.id})
            return url + f"?organization_id={self.org.pk}"

        self.login_as_child_member()
        params = json.dumps({"display_name": "quack"})

        # child users can update the sensors of their properties
        result = self.client.put(sensor_url(child_sensor), params, content_type="application/json")
        assert result.status_code == 200

        # but not the sensors of a root property, through the view of their own property
        result = self.client.put(sensor_url(s), params, content_type="application/json")
        assert result.status_code == 404
        result = self.client.delete(sensor_url(s))
        assert result.status_code == 404
        s.refresh_from_db()
        assert s.display_name == "s1"

    def test_update_sensor_cannot_move_it_to_another_data_logger(self):
        dl = DataLogger.objects.create(property_id=self.property_1.id, display_name="moo")
        other_dl = DataLogger.objects.create(property_id=self.property_2.id, display_name="boo")
        s = Sensor.objects.create(data_logger=dl, display_name="s1", sensor_type="first", units="one", column_name="sensor 1")

        url = reverse("api:v3:property-sensors-detail", kwargs={"property_pk": self.property_view_1.pk, "pk": s.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack", "data_logger_id": other_dl.id})
        result = self.client.put(url, params, content_type="application/json")

        assert result.status_code == 200
        s.refresh_from_db()
        assert s.display_name == "quack"
        assert s.data_logger_id == dl.id

    def test_update_data_logger_cannot_move_it_to_another_property(self):
        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        dl = DataLogger.objects.create(property_id=child_property.id, display_name="moo")

        url = reverse("api:v3:data_logger-detail", kwargs={"pk": dl.id})
        url += f"?organization_id={self.org.pk}"
        params = json.dumps({"display_name": "quack", "property": self.property_1.id})
        self.login_as_child_member()
        result = self.client.put(url, params, content_type="application/json")

        assert result.status_code == 200
        dl.refresh_from_db()
        assert dl.display_name == "quack"
        assert dl.property_id == child_property.id


class SensorReadingTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        property_view = FakePropertyViewFactory(organization=self.org).get_property_view()
        self.data_logger = DataLogger.objects.create(
            property_id=property_view.property.id,
            display_name="logger",
            is_occupied_data=[(datetime(2020, 1, 1, tzinfo=ZoneInfo(settings.TIME_ZONE)).isoformat(), True)],
        )
        self.sensor_1 = Sensor.objects.create(
            data_logger=self.data_logger, display_name="s1", sensor_type="t", units="u", column_name="sensor 1"
        )
        self.sensor_2 = Sensor.objects.create(
            data_logger=self.data_logger, display_name="s2", sensor_type="t", units="u", column_name="sensor 2"
        )
        self.timestamp = make_aware(datetime(2020, 1, 1, 12), timezone=ZoneInfo(settings.TIME_ZONE))

    def test_table_is_a_hypertable_partitioned_on_timestamp(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM timescaledb_information.dimensions WHERE hypertable_name = 'seed_sensorreading'",
            )
            self.assertEqual(cursor.fetchall(), [("timestamp",)])

    def test_pk_is_sensor_and_timestamp(self):
        reading = SensorReading.objects.create(sensor=self.sensor_1, timestamp=self.timestamp, reading=1, is_occupied=False)

        self.assertEqual(reading.pk, (self.sensor_1.id, self.timestamp))
        self.assertEqual(SensorReading.objects.get(pk=(self.sensor_1.id, self.timestamp)).reading, 1)

    def test_deleting_a_reading_instance_only_deletes_that_reading(self):
        reading_1 = SensorReading.objects.create(sensor=self.sensor_1, timestamp=self.timestamp, reading=1, is_occupied=False)
        SensorReading.objects.create(sensor=self.sensor_2, timestamp=self.timestamp, reading=2, is_occupied=False)

        reading_1.delete()

        self.assertEqual(list(SensorReading.objects.values_list("sensor_id", "reading")), [(self.sensor_2.id, 2)])

    def test_duplicate_sensor_and_timestamp_is_rejected(self):
        SensorReading.objects.create(sensor=self.sensor_1, timestamp=self.timestamp, reading=1, is_occupied=False)

        with pytest.raises(IntegrityError), transaction.atomic():
            SensorReading.objects.create(sensor=self.sensor_1, timestamp=self.timestamp, reading=2, is_occupied=False)

    def test_save_sensor_readings_task_updates_existing_readings(self):
        progress_data = ProgressData("save-sensor-readings-test", self.id())
        progress_data.total = 2
        progress_data.save()

        _save_sensor_readings_task([("2020-01-01 12:00:00", 1.0)], self.data_logger.id, self.sensor_1.column_name, progress_data.key)
        _save_sensor_readings_task([("2020-01-01 12:00:00", 2.0)], self.data_logger.id, self.sensor_2.column_name, progress_data.key)
        result = _save_sensor_readings_task(
            [("2020-01-01 12:00:00", 10.0)], self.data_logger.id, self.sensor_1.column_name, progress_data.key
        )

        self.assertEqual(result[self.sensor_1.column_name]["count"], 1)
        self.assertEqual(
            sorted(SensorReading.objects.values_list("sensor_id", "reading")),
            [(self.sensor_1.id, 10.0), (self.sensor_2.id, 2.0)],
        )
