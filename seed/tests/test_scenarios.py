# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import base64
import json

from django.urls import reverse_lazy
from django.utils.dateparse import parse_datetime

from seed.landing.models import SEEDUser as User
from seed.models import (
    Meter,
    MeterReading,
    Property,
    PropertyMeasure,
    PropertyView,
    Scenario
)
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyMeasureFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class TestScenarios(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)

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

    def test_delete_scenario(self):
        """
        Test that the scenario view can delete the scenario model
        """
        # -- Setup
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        scenario = Scenario.objects.create(property_state=property_state)

        self.assertEqual(Scenario.objects.count(), 1)

        # The Scenario view uses PropertyView.id not PropertyState.id
        response = self.client.delete(
            reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, scenario.id + 1]),
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Scenario.objects.count(), 1)

        response = self.client.delete(
            reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, scenario.id]),
            **self.headers
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Scenario.objects.count(), 0)

    def test_delete_scenarios_with_measures(self):
        property_state = FakePropertyMeasureFactory(self.org).get_property_state()
        property = self.property_factory.get_property()
        property_view = PropertyView.objects.create(property=property, cycle_id=1, state=property_state)
        scenario = Scenario.objects.create(property_state=property_state)
        measures = property_state.measure_set.all()
        property_measures = PropertyMeasure.objects.filter(measure__in=measures)

        # assign property_measures to scneario
        for pm in property_measures:
            pm.scenario_set.set([scenario])

        self.assertEqual(PropertyMeasure.objects.count(), 5)
        self.assertEqual(Scenario.objects.count(), 1)

        response = self.client.delete(
            reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, scenario.id]),
            **self.headers
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(PropertyMeasure.objects.count(), 0)
        self.assertEqual(Scenario.objects.count(), 0)

    def test_update_scenario(self):
        """
        Test that the scenario view can edit/update the scenario model
        """

        # -- Setup
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        scenario = Scenario.objects.create(property_state=property_state, temporal_status=3, name='name1')

        self.assertEqual(Scenario.objects.count(), 1)
        self.assertEqual(scenario.temporal_status, 3)

        scenario_fields = {
            'temporal_status': 5,
            'name': 'name2'
        }

        response = self.client.put(
            reverse_lazy(
                'api:v3:property-scenarios-detail',
                args=[property_view.id, scenario.id]
            ),
            data=json.dumps(scenario_fields),
            content_type='application/json',
            **self.headers
        )

        scenario = Scenario.objects.get(id=scenario.id)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(scenario.temporal_status, 5)
        self.assertEqual(scenario.name, 'name2')

    def test_fails_to_update_scenario_with_invalid_field(self):
        """
        Test the failure response when invalid field names are passed
        """
        # -- Setup
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        scenario = Scenario.objects.create(property_state=property_state, temporal_status=3)

        scenario_fields = {
            'temporal_status': 5,
            'invalid_field': '123'
        }

        response = self.client.put(
            reverse_lazy(
                'api:v3:property-scenarios-detail',
                args=[property_view.id, scenario.id]
            ),
            data=json.dumps(scenario_fields),
            content_type='application/json',
            **self.headers
        )

        scenario = Scenario.objects.get(id=scenario.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['Success'], False)
        self.assertEqual(response.json()['Message'], '"invalid_field" is not a valid scenario field')

    def test_get_scenarios(self):
        """
        Test retrieve and list endpoints for Scenario view
        """
        property_view = self.property_view_factory.get_property_view()
        property_state = property_view.state
        scenario0 = Scenario.objects.create(property_state=property_state, name='scenario 0')
        scenario1 = Scenario.objects.create(property_state=property_state, name='scenario 1')

        url = reverse_lazy('api:v3:property-scenarios-list', args=[property_view.id])
        response = self.client.get(
            url,
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]['name'], 'scenario 0')
        self.assertEqual(response.json()[1]['name'], 'scenario 1')

        url = reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, scenario0.id])
        response = self.client.get(
            url,
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'scenario 0')

        url = reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, scenario1.id])
        response = self.client.get(
            url,
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'scenario 1')

        url = reverse_lazy('api:v3:property-scenarios-detail', args=[property_view.id, 100])
        response = self.client.get(
            url,
            **self.headers
        )
        self.assertEqual(response.status_code, 404)
