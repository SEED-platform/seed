# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

from django.urls import reverse
from django.utils.timezone import \
    make_aware  # make_aware is used because inconsistencies exist in creating datetime with tzinfo
from pytz import timezone

from config.settings.common import TIME_ZONE
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
        url = reverse('api:v3:data_logger-list') + "?property_view_id=" + str(self.property_view_1.id)
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
        url = reverse('api:v3:data_logger-list')
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
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })

        url = reverse('api:v3:data_logger-detail', kwargs={'pk': dl.id})
        url += f'?organization_id={self.org.pk}'

        # child user cannot
        self.login_as_child_member()
        result = self.client.delete(url)
        assert result.status_code == 404

        # root users can get data logger in root
        self.login_as_root_member()
        result = self.client.delete(url)
        assert result.status_code == 204

    def test_delete_sensor_permissions(self):
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })

        url = reverse('api:v3:property-sensors-detail', kwargs={'property_pk': self.property_view_1.pk, "pk": s.id})
        url += f'?organization_id={self.org.pk}'

        # child user cannot
        self.login_as_child_member()
        result = self.client.delete(url)
        assert result.status_code == 404

        # root users can get data logger in root
        self.login_as_root_member()
        result = self.client.delete(url)
        assert result.status_code == 204

    def test_update_data_logger_permissions(self):
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })

        url = reverse('api:v3:data_logger-detail', kwargs={'pk': dl.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "quack"
        })

        # child user cannot
        self.login_as_child_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 404

        # root users can
        self.login_as_root_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 200

    def test_update_sensor_permissions(self):
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })

        url = reverse('api:v3:property-sensors-detail', kwargs={'property_pk': self.property_view_1.pk, "pk": s.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "quack"
        })

        # child user cannot
        self.login_as_child_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 404

        # root users can
        self.login_as_root_member()
        result = self.client.put(url, params, content_type="application/json")
        assert result.status_code == 200

    def test_property_sensors_endpoint_returns_a_list_of_sensors_of_a_view(self):
        dl_a = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        Sensor.objects.create(**{
            "data_logger": dl_a,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })
        Sensor.objects.create(**{
            "data_logger": dl_a,
            "display_name": "s2",
            "sensor_type": "second",
            "units": "two",
            "column_name": "sensor 2"
        })

        dl_b = DataLogger.objects.create(**{
            "property_id": self.property_2.id,
            "display_name": "boo",
        })
        Sensor.objects.create(**{
            "data_logger": dl_b,
            "display_name": "s3",
            "sensor_type": "third",
            "units": "three",
            "column_name": "sensor 3"
        })

        url = reverse('api:v3:property-sensors-list', kwargs={'property_pk': self.property_view_1.id})
        url += f'?organization_id={self.org.pk}'

        result = self.client.get(url)
        result_dict = json.loads(result.content)

        self.assertCountEqual([r["column_name"] for r in result_dict], ["sensor 1", "sensor 2"])

        url = reverse('api:v3:property-sensors-list', kwargs={'property_pk': self.property_view_2.id})
        url += f'?organization_id={self.org.pk}'

        result = self.client.get(url)
        result_dict = json.loads(result.content)

        self.assertCountEqual([r["column_name"] for r in result_dict], ["sensor 3"])

    def test_delete_sensor(self):
        dl_1 = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s1 = Sensor.objects.create(**{
            "data_logger": dl_1,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })
        SensorReading.objects.create(**{
            "reading": 0.0,
            "timestamp": str(datetime(2000, 1, 1, tzinfo=timezone(TIME_ZONE))),
            "sensor": s1,
            "is_occupied": False
        })

        dl_2 = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "bark",
        })
        s2 = Sensor.objects.create(**{
            "data_logger": dl_2,
            "display_name": "s2",
            "sensor_type": "second",
            "units": "two",
            "column_name": "sensor 2"
        })
        SensorReading.objects.create(**{
            "reading": 0.0,
            "timestamp": str(datetime(2000, 1, 1, tzinfo=timezone(TIME_ZONE))),
            "sensor": s2,
            "is_occupied": False
        })

        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 2
        assert SensorReading.objects.count() == 2

        # Action
        url = reverse('api:v3:property-sensors-detail', kwargs={'property_pk': self.property_view_1.pk, "pk": s1.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.delete(url, content_type="application/json")

        # Assertion
        assert result.status_code == 204
        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 1
        assert SensorReading.objects.count() == 1

    def test_property_sensor_usage_returns_sensor_readings(self):
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s1 = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })
        s2 = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s2",
            "sensor_type": "second",
            "units": "two",
            "column_name": "sensor 2"
        })

        tz_obj = timezone(TIME_ZONE)
        timestamps = [
            make_aware(datetime(year, month, day), timezone=tz_obj)
            for day in [10, 20]
            for month in [1, 2]
            for year in [2000, 2100]
        ]

        s1_reading = 0.0
        s2_reading = 10.0
        except_results = []
        for timestamp in timestamps:
            SensorReading.objects.create(**{
                "reading": s1_reading,
                "timestamp": timestamp,
                "sensor": s1,
                "is_occupied": False
            })
            SensorReading.objects.create(**{
                "reading": s2_reading,
                "timestamp": timestamp,
                "sensor": s2,
                "is_occupied": False
            })
            except_results.append({
                "timestamp": str(timestamp.replace(tzinfo=None)),
                f"{s1.display_name} ({dl.display_name})": s1_reading,
                f"{s2.display_name} ({dl.display_name})": s2_reading
            })
            s1_reading += 1
            s2_reading += 1

        url = reverse('api:v3:property-sensors-usage', kwargs={'property_pk': self.property_view_1.id})
        url += f'?organization_id={self.org.pk}'
        post_params = json.dumps({
            'interval': 'Exact',
            'excluded_sensor_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)
        self.assertCountEqual(result_dict["readings"], except_results)

        url = reverse('api:v3:property-sensors-usage', kwargs={'property_pk': self.property_view_1.id})
        url += f'?organization_id={self.org.pk}'
        post_params = json.dumps({
            'interval': 'Month',
            'excluded_sensor_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)

        self.assertCountEqual(
            result_dict["readings"],
            [
                {'month': 'January 2000', 's1 (moo)': 2.0, 's2 (moo)': 12.0},
                {'month': 'February 2000', 's1 (moo)': 4.0, 's2 (moo)': 14.0},
                {'month': 'January 2100', 's1 (moo)': 3.0, 's2 (moo)': 13.0},
                {'month': 'February 2100', 's1 (moo)': 5.0, 's2 (moo)': 15.0}
            ]
        )

        url = reverse('api:v3:property-sensors-usage', kwargs={'property_pk': self.property_view_1.id})
        url += f'?organization_id={self.org.pk}'
        post_params = json.dumps({
            'interval': 'Year',
            'excluded_sensor_ids': [],
        })
        result = self.client.post(url, post_params, content_type="application/json")
        result_dict = json.loads(result.content)

        self.assertCountEqual(
            result_dict["readings"],
            [
                {'year': 2000, 's1 (moo)': 3.0, 's2 (moo)': 13.0},
                {'year': 2100, 's1 (moo)': 4.0, 's2 (moo)': 14.0},
            ]
        )

    def test_delete_data_logger(self):
        dl_1 = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s1 = Sensor.objects.create(**{
            "data_logger": dl_1,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })
        SensorReading.objects.create(**{
            "reading": 0.0,
            "timestamp": str(datetime(2000, 1, 1, tzinfo=timezone(TIME_ZONE))),
            "sensor": s1,
            "is_occupied": False
        })

        dl_2 = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "bark",
        })
        s2 = Sensor.objects.create(**{
            "data_logger": dl_2,
            "display_name": "s2",
            "sensor_type": "second",
            "units": "two",
            "column_name": "sensor 2"
        })
        SensorReading.objects.create(**{
            "reading": 0.0,
            "timestamp": str(datetime(2000, 1, 1, tzinfo=timezone(TIME_ZONE))),
            "sensor": s2,
            "is_occupied": False
        })

        assert DataLogger.objects.count() == 2
        assert Sensor.objects.count() == 2
        assert SensorReading.objects.count() == 2

        # Action
        url = reverse('api:v3:data_logger-detail', kwargs={'pk': dl_1.id})
        url += f'?organization_id={self.org.pk}'
        result = self.client.delete(url, content_type="application/json")

        # Assertion
        assert result.status_code == 204
        assert DataLogger.objects.count() == 1
        assert Sensor.objects.count() == 1
        assert SensorReading.objects.count() == 1

    def test_update_data_logger(self):
        # Set Up
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })

        # Action
        url = reverse('api:v3:data_logger-detail', kwargs={'pk': dl.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "quack"
        })
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 200
        assert DataLogger.objects.first().display_name == "quack"

    def test_update_data_logger_duplicate_display_name(self):
        # Set Up
        DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "quack",
        })
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })

        # Action
        url = reverse('api:v3:data_logger-detail', kwargs={'pk': dl.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "quack"
        })
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 400

    def test_update_sensor(self):
        # Set Up
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })

        # Action
        url = reverse('api:v3:property-sensors-detail', kwargs={'property_pk': self.property_view_1.pk, "pk": s.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "quack"
        })
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 200
        assert Sensor.objects.first().display_name == "quack"

    def test_update_sensor_duplicate_display_name(self):
        # Set Up
        dl = DataLogger.objects.create(**{
            "property_id": self.property_1.id,
            "display_name": "moo",
        })
        s1 = Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s1",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 1"
        })
        Sensor.objects.create(**{
            "data_logger": dl,
            "display_name": "s2",
            "sensor_type": "first",
            "units": "one",
            "column_name": "sensor 2"
        })

        # Action
        url = reverse('api:v3:property-sensors-detail', kwargs={'property_pk': self.property_view_1, "pk": s1.id})
        url += f'?organization_id={self.org.pk}'
        params = json.dumps({
            "display_name": "s2"
        })
        result = self.client.put(url, params, content_type="application/json")

        # Assert
        assert result.status_code == 400
