# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.utils.dateparse import parse_datetime

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakePropertyMeasureFactory, FakePropertyStateFactory
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization
from seed.models import Scenario, Meter, MeterReading, Property, PropertyView


class TestMeasures(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_scenario_meters(self):
        ps = FakePropertyMeasureFactory(self.org).get_property_state()

        self.assertEqual(ps.measures.count(), 5)
        self.assertEqual(ps.propertymeasure_set.count(), 5)

        # for m in ps.propertymeasure_set.all():
        #     print(m.measure)
        #     print(m.cost_mv)

        # s = Scenario.objects.create(
        #     name='Test'
        # )
        # s.property_state = ps
        # s.save()

        # create a new meter
        # s.meters.add()

    def test_copy_initial_meters_regression_1933(self):
        """This test tracks the bug from GH issue 1933
        When updating a property with a BuildingSync file, cloned meter readings were
        not being linked to cloned meters.
        """
        # -- Setup
        property_state = self.property_state_factory.get_property_state()
        source_scenario = Scenario.objects.create(property_state=property_state)

        # create new property, state, and view
        new_property_state = self.property_state_factory.get_property_state()
        new_property = Property.objects.create(organization_id=1)
        PropertyView.objects.create(cycle_id=1, state_id=new_property_state.id,
                                    property_id=new_property.id)
        new_scenario = Scenario.objects.create(property_state=new_property_state)

        # create a meter and meter readings for the source
        meter = Meter.objects.create(scenario_id=source_scenario.id)
        MeterReading.objects.create(meter=meter,
                                    start_time=parse_datetime('2016-10-03T19:00:00+0200'),
                                    end_time=parse_datetime('2016-10-04T19:00:00+0200'),
                                    conversion_factor=1.0)
        self.assertEqual(MeterReading.objects.filter(meter_id=meter.id).count(), 1)

        # -- Act
        # call copy_initial_meters
        new_scenario.copy_initial_meters(source_scenario.id)

        # -- Assert
        new_meter = Meter.objects.filter(scenario=new_scenario, property=new_property)
        self.assertEqual(new_meter.count(), 1)
        self.assertEqual(new_meter.first().meter_readings.count(), 1)
