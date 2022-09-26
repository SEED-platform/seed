# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from seed.models import Column, ComplianceMetric, User
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeDerivedColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.utils.organizations import create_organization


class ComplianceMetricViewTests(TestCase):
    """
    Test ComplianceMetric model
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.client.login(**user_details)
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle A")
        self.cycle2 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle B")
        self.cycle3 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle C")
        self.cycle4 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle D")

        self.column1 = Column.objects.create(column_name='column 1', organization=self.org,)
        self.column2 = Column.objects.create(column_name='column 2', organization=self.org,)
        self.column3 = Column.objects.create(column_name='column 3', organization=self.org,)
        self.column4 = Column.objects.create(column_name='column 4', organization=self.org,)
        self.column5 = Column.objects.create(column_name='column 5', organization=self.org,)
        self.column6 = Column.objects.create(column_name='column 6', organization=self.org,)
        self.column7 = Column.objects.create(column_name='column 7', organization=self.org,)

        self.x_axes1 = [self.column5, self.column6, self.column7]
        self.x_axes2 = [self.column7]

        # first metric (combined energy and emission)
        self.compliance_metric1 = ComplianceMetric.objects.create(
            name='compliance metric 1',
            organization=self.org,
            start=datetime(2017, 1, 1, tzinfo=timezone.utc),
            end=datetime(2021, 12, 31, tzinfo=timezone.utc),
            actual_energy_column=self.column1,
            target_energy_column=self.column2,
            energy_metric_type=0,
            actual_emission_column=self.column3,
            target_emission_column=self.column4,
            emission_metric_type=1
        )

        self.compliance_metric1.x_axis_columns.set(self.x_axes1)

        # 2nd metric (just energy)
        self.compliance_metric2 = ComplianceMetric.objects.create(
            name='compliance metric 2',
            organization=self.org,
            start=datetime(2018, 1, 1, tzinfo=timezone.utc),
            end=datetime(2022, 12, 31, tzinfo=timezone.utc),
            actual_energy_column=self.column1,
            target_energy_column=self.column2,
            energy_metric_type=0
        )
        self.compliance_metric2.x_axis_columns.set(self.x_axes2)

    def test_compliance_metric_model(self):
        compliance_metrics = ComplianceMetric.objects.all().order_by('created')
        self.assertEqual(2, len(compliance_metrics))

        compliance_metrics1 = compliance_metrics[0]
        self.assertIsNotNone(compliance_metrics1.energy_metric_type)
        self.assertIsNotNone(compliance_metrics1.emission_metric_type)

        compliance_metrics1.x_axis_columns.all()

        self.assertEqual(len(compliance_metrics1.x_axis_columns.all()), 3)

        compliance_metrics2 = compliance_metrics[1]
        self.assertIsNotNone(compliance_metrics2.energy_metric_type)
        self.assertIsNone(compliance_metrics2.actual_emission_column)
        self.assertIsNone(compliance_metrics2.target_emission_column)
        self.assertEqual(len(compliance_metrics2.x_axis_columns.all()), 1)

    def test_compliance_metric_create_endpoint(self):
        self.assertEqual(2, len(ComplianceMetric.objects.all()))

        response = self.client.get(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(2, len(data['compliance_metrics']))

        response = self.client.post(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "compliance metric 3",
                "start": "2018-01-01",
                "end": "2022-12-31",
                "actual_emission_column": self.column3.id,
                "target_emission_column": self.column4.id,
                "emission_metric_type": "Target > Actual for Compliance",
                "x_axis_columns": [self.column5.id, self.column6.id]

            }),
            content_type='application/json'
        )
        data = json.loads(response.content)

        self.assertEqual('compliance metric 3', data['compliance_metric']['name'])
        self.assertEqual(self.org.id, data['compliance_metric']['organization_id'])
        self.assertTrue(bool(data['compliance_metric']['id']))
        self.assertEqual(data['compliance_metric']['actual_emission_column'], self.column3.id)
        self.assertEqual(data['compliance_metric']['target_emission_column'], self.column4.id)
        self.assertEqual(len(data['compliance_metric']['x_axis_columns']), 2)

        self.assertEqual(3, len(ComplianceMetric.objects.all()))

        response = self.client.get(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(3, len(data['compliance_metrics']))

        compliance_metric = ComplianceMetric.objects.get(name='compliance metric 3')
        response = self.client.delete(
            reverse('api:v3:compliance_metrics-detail', args=[compliance_metric.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        response = self.client.get(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(2, len(data['compliance_metrics']))
        self.assertEqual(2, len(ComplianceMetric.objects.all()))

    def test_compliance_metric_create_bad_data(self):
        response = self.client.post(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "compliance_metric3",
                "energy_metric_type": 0
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        expected = 'Data Validation Error'
        self.assertEqual(expected, data['message'])

    def test_compliance_metric_retrieve_endpoint(self):
        response = self.client.get(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric1.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('compliance metric 1', data['compliance_metric']['name'])
        self.assertEqual(self.column5.id, data['compliance_metric']['x_axis_columns'][0])

        response = self.client.get(
            reverse('api:v3:compliance_metrics-detail', args=[99999999]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('ComplianceMetric with id 99999999 does not exist', data['message'])

    def test_data_view_update_endpoint(self):
        self.assertEqual('compliance metric 1', self.compliance_metric1.name)
        self.assertEqual(3, len(self.compliance_metric1.x_axis_columns.all()))

        response = self.client.put(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "updated name",
                "x_axis_columns": [self.column3.id, self.column4.id]
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('updated name', data['compliance_metric']['name'])
        self.assertEqual(2, len(data['compliance_metric']['x_axis_columns']))

        cm1 = ComplianceMetric.objects.get(id=self.compliance_metric1.id)
        self.assertEqual('updated name', cm1.name)
        self.assertEqual(2, len(cm1.x_axis_columns.all()))
        self.assertEqual(self.column3.id, cm1.x_axis_columns.first().id)

        response = self.client.put(
            reverse('api:v3:compliance_metrics-detail', args=[99999]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "x_axis_columns": [self.column1.id, self.column2.id, self.column3.id],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('ComplianceMetric with id 99999 does not exist', data['message'])


# TODO: add tests for calculating compliance metrics
