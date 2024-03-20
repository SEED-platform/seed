# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
import json

from django.core import serializers
from django.urls import reverse

from seed.models import ComplianceMetric, FilterGroup
from seed.tests.util import AccessLevelBaseTestCase


class ComplianceMetricViewTests(AccessLevelBaseTestCase):
    """
    Test ComplianceMetric model
    """

    def setUp(self):

        # set up org, all users, and factories
        super().setUp()

        self.cycle1 = self.cycle_factory.get_cycle(name="Cycle A")
        self.cycle2 = self.cycle_factory.get_cycle(name="Cycle B")
        self.cycle3 = self.cycle_factory.get_cycle(name="Cycle C")
        self.cycle4 = self.cycle_factory.get_cycle(name="Cycle D")

        self.column1 = self.column_factory.get_column('column 1', is_extra_data=True)
        self.column2 = self.column_factory.get_column('column 2', is_extra_data=True)
        self.column3 = self.column_factory.get_column('column 3', is_extra_data=True)
        self.column4 = self.column_factory.get_column('column 4', is_extra_data=True)
        self.column5 = self.column_factory.get_column('column 5', is_extra_data=True)
        self.column6 = self.column_factory.get_column('column 6', is_extra_data=True)
        self.column7 = self.column_factory.get_column('column 7', is_extra_data=True)

        self.x_axes1 = [self.column5, self.column6, self.column7]
        self.x_axes2 = [self.column7]

        self.cycles1 = [self.cycle1, self.cycle2, self.cycle3]
        self.cycles2 = [self.cycle4]

        self.filter_group = FilterGroup.objects.create(
            name='filter group 1',
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={'year_built__lt': ['1980']},
        )
        self.filter_group.save()

        # first metric (combined energy and emission with filter group)
        self.compliance_metric1 = ComplianceMetric.objects.create(
            name='compliance metric 1',
            organization=self.org,
            actual_energy_column=self.column1,
            target_energy_column=self.column2,
            energy_metric_type=0,
            actual_emission_column=self.column3,
            target_emission_column=self.column4,
            emission_metric_type=1,
            filter_group=self.filter_group
        )
        self.compliance_metric1.cycles.set(self.cycles1)
        self.compliance_metric1.x_axis_columns.set(self.x_axes1)

        # 2nd metric (just energy without filter group)
        self.compliance_metric2 = ComplianceMetric.objects.create(
            name='compliance metric 2',
            organization=self.org,
            actual_energy_column=self.column1,
            target_energy_column=self.column2,
            energy_metric_type=0
        )
        self.compliance_metric2.x_axis_columns.set(self.x_axes2)
        self.compliance_metric2.cycles.set(self.cycles2)

    def test_compliance_metric_model(self):
        compliance_metrics = ComplianceMetric.objects.all().order_by('created')
        self.assertEqual(2, len(compliance_metrics))

        compliance_metrics1 = compliance_metrics[0]
        self.assertIsNotNone(compliance_metrics1.energy_metric_type)
        self.assertIsNotNone(compliance_metrics1.emission_metric_type)
        self.assertIsNotNone(compliance_metrics1.filter_group)

        compliance_metrics1.x_axis_columns.all()

        self.assertEqual(len(compliance_metrics1.x_axis_columns.all()), 3)
        self.assertEqual(len(compliance_metrics1.cycles.all()), 3)

        compliance_metrics2 = compliance_metrics[1]
        self.assertIsNotNone(compliance_metrics2.energy_metric_type)
        self.assertIsNone(compliance_metrics2.actual_emission_column)
        self.assertIsNone(compliance_metrics2.target_emission_column)
        self.assertEqual(len(compliance_metrics2.x_axis_columns.all()), 1)
        self.assertEqual(len(compliance_metrics2.cycles.all()), 1)
        self.assertIsNone(compliance_metrics2.filter_group)

    def test_compliance_metric_create_endpoint(self):
        self.assertEqual(2, len(ComplianceMetric.objects.all()))

        test_metric_details = {
            "name": "compliance metric 3",
            "actual_emission_column": self.column3.id,
            "target_emission_column": self.column4.id,
            "emission_metric_type": "Target > Actual for Compliance",
            "filter_group": self.filter_group.id,
            "cycles": [self.cycle1.id, self.cycle2.id],
            "x_axis_columns": [self.column5.id, self.column6.id]
        }

        # can create as ROOT-LEVEL OWNER
        self.login_as_root_owner()
        response = self.client.get(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(2, len(data['compliance_metrics']))

        response = self.client.post(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(test_metric_details),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)

        self.assertEqual('compliance metric 3', data['compliance_metric']['name'])
        self.assertEqual(self.org.id, data['compliance_metric']['organization_id'])
        self.assertTrue(bool(data['compliance_metric']['id']))
        self.assertEqual(data['compliance_metric']['actual_emission_column'], self.column3.id)
        self.assertEqual(data['compliance_metric']['target_emission_column'], self.column4.id)
        self.assertEqual(len(data['compliance_metric']['x_axis_columns']), 2)
        self.assertEqual(len(data['compliance_metric']['cycles']), 2)
        self.assertTrue(bool(data['compliance_metric']['filter_group']))

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

        # CAN CREATE as ROOT-LEVEL MEMBER:
        self.login_as_root_member()
        test_metric_details['name'] = "compliance ROOT MEMBER"

        response = self.client.post(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(test_metric_details),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # CANNOT CREATE AS CHILD-LEVEL MEMBER:
        self.login_as_child_member()
        test_metric_details['name'] = "compliance CHILD MEMBER"
        response = self.client.post(
            reverse('api:v3:compliance_metrics-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps(test_metric_details),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

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
        self.login_as_child_member()
        response = self.client.get(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric1.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('compliance metric 1', data['compliance_metric']['name'])
        self.assertEqual([self.column5.id, self.column6.id, self.column7.id], data['compliance_metric']['x_axis_columns'])

        response = self.client.get(
            reverse('api:v3:compliance_metrics-detail', args=[99999999]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('ComplianceMetric with id 99999999 does not exist', data['message'])

    def test_compliance_metric_update_endpoint(self):
        self.assertEqual('compliance metric 1', self.compliance_metric1.name)
        self.assertEqual(3, len(self.compliance_metric1.x_axis_columns.all()))

        # CAN UPDATE as ROOT-LEVEL MEMBER:
        self.login_as_root_member()
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

        # test cannot update a non-existing compliance metric
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

        # CANNOT UPDATE AS CHILD-LEVEL MEMBER:
        self.login_as_child_member()
        response = self.client.put(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "another name"
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual(response.status_code, 403)

        cm1 = ComplianceMetric.objects.get(id=self.compliance_metric1.id)
        self.assertEqual('updated name', cm1.name)
        self.assertEqual(2, len(cm1.x_axis_columns.all()))
        self.assertEqual(self.column3.id, cm1.x_axis_columns.first().id)

    def test_compliance_metric_delete_endpoint(self):

        # CANNOT DELETE AS CHILD-LEVEL MEMBER:
        self.login_as_child_member()
        response = self.client.delete(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric2.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual(response.status_code, 403)

        compliance_metrics = ComplianceMetric.objects.all().order_by('created')
        self.assertEqual(2, len(compliance_metrics))

        # CAN DELETE AS ROOT-LEVEL MEMBER:
        self.login_as_root_member()
        response = self.client.delete(
            reverse('api:v3:compliance_metrics-detail', args=[self.compliance_metric2.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual(response.status_code, 200)

        compliance_metrics = ComplianceMetric.objects.all().order_by('created')
        self.assertEqual(1, len(compliance_metrics))


class ComplianceMetricEvaluationTests(AccessLevelBaseTestCase):
    """
    Test ComplianceMetric model's ability to evaluate propertyview values
    """
    def setUp(self):

        # set up org, all users, and factories
        super().setUp()

        self.cycle1 = self.cycle_factory.get_cycle(name="Cycle A")
        self.cycle2 = self.cycle_factory.get_cycle(name="Cycle B")
        self.cycle3 = self.cycle_factory.get_cycle(name="Cycle C")

        self.site_eui = self.column_factory.get_column('site_eui')
        self.total_ghg_emissions = self.column_factory.get_column('total_ghg_emissions')
        self.source_eui = self.column_factory.get_column('source_eui')
        self.total_marginal_ghg_emissions = self.column_factory.get_column('total_marginal_ghg_emissions')
        self.column5 = self.column_factory.get_column('column 5', is_extra_data=True)

        self.x_axes = [self.column5]

        self.cycles = [self.cycle1, self.cycle2, self.cycle3]

        self.filter_group = FilterGroup.objects.create(
            name='filter group 1',
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={'year_built__lt': ['1980']},
        )
        self.filter_group.save()

        # metric (just energy without filter group)
        self.compliance_metric = ComplianceMetric.objects.create(
            name='compliance metric 1',
            organization=self.org,
            actual_energy_column=self.site_eui,
            target_energy_column=self.source_eui,
            energy_metric_type=0
        )
        self.compliance_metric.x_axis_columns.set(self.x_axes)
        self.compliance_metric.cycles.set(self.cycles)

        # generate two different types of properties (2 for root and 2 for child)
        self.office1 = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.office2 = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.retail3 = self.property_factory.get_property(access_level_instance=self.root_level_instance)
        self.retail4 = self.property_factory.get_property(access_level_instance=self.child_level_instance)

        self.view10 = self.property_view_factory.get_property_view(prprty=self.office1, cycle=self.cycle1, site_eui=60, source_eui=59, total_ghg_emissions=500)
        self.view11 = self.property_view_factory.get_property_view(prprty=self.office2, cycle=self.cycle1, site_eui=70, source_eui=59, total_ghg_emissions=400)
        self.view12 = self.property_view_factory.get_property_view(prprty=self.retail3, cycle=self.cycle1, site_eui=65, source_eui=62, total_ghg_emissions=300)
        self.view13 = self.property_view_factory.get_property_view(prprty=self.retail4, cycle=self.cycle1, site_eui=72, source_eui=62, total_ghg_emissions=350)

        serializers.serialize('json', [self.view10])

        self.view20 = self.property_view_factory.get_property_view(prprty=self.office1, cycle=self.cycle2, site_eui=58, source_eui=59, total_ghg_emissions=480)
        self.view21 = self.property_view_factory.get_property_view(prprty=self.office2, cycle=self.cycle2, site_eui=68, source_eui=59, total_ghg_emissions=380)
        self.view22 = self.property_view_factory.get_property_view(prprty=self.retail3, cycle=self.cycle2, site_eui=63, source_eui=59, total_ghg_emissions=280)
        self.view23 = self.property_view_factory.get_property_view(prprty=self.retail4, cycle=self.cycle2, site_eui=70, source_eui=59, total_ghg_emissions=330)

    # calculating compliance metrics
    def test_compliance_metric_get_data_permissions(self):

        # login as root level owner/member and retrieve data
        self.login_as_root_owner()
        response = self.client.get(
            reverse('api:v3:compliance_metrics-evaluate', args=[self.compliance_metric.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        self.assertEqual('success', data['status'])

        properties_by_cycle = data['data']['properties_by_cycles'][str(self.cycle1.id)]
        self.assertEqual(len(properties_by_cycle), 4)

        self.login_as_root_member()
        response = self.client.get(
            reverse('api:v3:compliance_metrics-evaluate', args=[self.compliance_metric.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        self.assertEqual('success', data['status'])

        properties_by_cycle = data['data']['properties_by_cycles'][str(self.cycle1.id)]
        self.assertEqual(len(properties_by_cycle), 4)

        # login as child and retrieve data
        self.login_as_child_member()
        response = self.client.get(
            reverse('api:v3:compliance_metrics-evaluate', args=[self.compliance_metric.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        self.assertEqual('success', data['status'])

        properties_by_cycle = data['data']['properties_by_cycles'][str(self.cycle1.id)]
        self.assertEqual(len(properties_by_cycle), 2)
