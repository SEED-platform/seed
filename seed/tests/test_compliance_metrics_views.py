# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from django.core import serializers
from django.test import TestCase
from django.urls import reverse

from seed.models import (
    ComplianceMetric,
    FilterGroup,
    User
)
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
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
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

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
            inventory_type=1,  # Tax Lot
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
                "actual_emission_column": self.column3.id,
                "target_emission_column": self.column4.id,
                "emission_metric_type": "Target > Actual for Compliance",
                "filter_group": self.filter_group.id,
                "cycles": [self.cycle1.id, self.cycle2.id],
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

class ComplianceMetricEvaluationTests(TestCase):
    """
    Test ComplianceMetric model's ability to evaluate propertyview values
    """
    def setUp(self):
        # root user
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

        # setup factories
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)


        # child user
        self.user_with_nothing_details = {
            'username': 'nothing@demo.com',
            'password': 'test_pass',
        }
        self.user_with_nothing = User.objects.create_user(**self.user_with_nothing_details)
        # add ALI and user to org
        self.org.access_level_names = ["root", "child"]
        child = self.org.add_new_access_level_instance(self.org.root.id, "child")
        self.org.add_member(self.user_with_nothing, child.pk)
        self.org.save()

        self.client.login(**user_details)
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
            inventory_type=1,  # Tax Lot
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
        self.office1 = self.property_factory.get_property(access_level_instance=self.org.root)
        self.office2 = self.property_factory.get_property(access_level_instance=child)
        self.retail3 = self.property_factory.get_property(access_level_instance=self.org.root)
        self.retail4 = self.property_factory.get_property(access_level_instance=child)

        self.view10 = self.property_view_factory.get_property_view(prprty=self.office1, cycle=self.cycle1, site_eui=60, source_eui=59, total_ghg_emissions=500)
        self.view11 = self.property_view_factory.get_property_view(prprty=self.office2, cycle=self.cycle1, site_eui=70, source_eui=59, total_ghg_emissions=400)
        self.view12 = self.property_view_factory.get_property_view(prprty=self.retail3, cycle=self.cycle1, site_eui=65, source_eui=62, total_ghg_emissions=300)
        self.view13 = self.property_view_factory.get_property_view(prprty=self.retail4, cycle=self.cycle1, site_eui=72, source_eui=62, total_ghg_emissions=350)

        data = serializers.serialize('json', [self.view10])
        print(f"view data: {data}")

        self.view20 = self.property_view_factory.get_property_view(prprty=self.office1, cycle=self.cycle2, site_eui=58, source_eui=59, total_ghg_emissions=480)
        self.view21 = self.property_view_factory.get_property_view(prprty=self.office2, cycle=self.cycle2, site_eui=68, source_eui=59, total_ghg_emissions=380)
        self.view22 = self.property_view_factory.get_property_view(prprty=self.retail3, cycle=self.cycle2, site_eui=63, source_eui=59, total_ghg_emissions=280)
        self.view23 = self.property_view_factory.get_property_view(prprty=self.retail4, cycle=self.cycle2, site_eui=70, source_eui=59, total_ghg_emissions=330)

    # calculating compliance metrics
    def test_compliance_metric_get_data_permissions(self):

        # logged in as root and retrieve data
        response = self.client.get(
            reverse('api:v3:compliance_metrics-evaluate', args=[self.compliance_metric.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        self.assertEqual('success', data['status'])

        print(f" DATA root: {data}")

        # # login as child and retrieve data
        # self.client.login(**self.user_with_nothing_details)
        # response = self.client.get(
        #     reverse('api:v3:compliance_metrics-evaluate', args=[self.compliance_metric.id]) + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # assert response.status_code == 200
        # data = json.loads(response.content)
        # self.assertEqual('success', data['status'])

        # print(f" DATA child: {data}")

        # data = data['data']
        # self.assertEqual(['meta', 'views_by_filter_group_id', 'columns_by_id', 'graph_data'], list(data.keys()))

        # graph_data = data['graph_data']

        # self.assertEqual(['organization', 'data_view'], list(data['meta'].keys()))

        # self.assertEqual({str(self.office_filter_group.id), str(self.retail_filter_group.id)}, set(data['views_by_filter_group_id']))

        # office = data['views_by_filter_group_id'][str(self.office_filter_group.id)]
        # retail = data['views_by_filter_group_id'][str(self.retail_filter_group.id)]

        # self.assertEqual([self.view10.state.address_line_1], sorted(list(data['views_by_filter_group_id'][str(self.office_filter_group.id)].values())))
        # self.assertEqual([], sorted(list(data['views_by_filter_group_id'][str(self.retail_filter_group.id)].values())))

        # data = data['columns_by_id']
        # self.assertEqual([str(self.site_eui.id), str(self.ghg.id)], list(data.keys()))
        # self.assertEqual(['filter_groups_by_id', 'unit'], list(data[str(self.site_eui.id)].keys()))
        # self.assertEqual('kBtu/ft²/year', data[str(self.site_eui.id)]['unit'])
        # self.assertEqual('t/year', data[str(self.ghg.id)]['unit'])

        # office = data[str(self.site_eui.id)]['filter_groups_by_id'][str(self.office_filter_group.id)]
        # retail = data[str(self.site_eui.id)]['filter_groups_by_id'][str(self.retail_filter_group.id)]
        # self.assertEqual(['cycles_by_id'], list(office.keys()))
        # self.assertEqual(['cycles_by_id'], list(retail.keys()))

        # self.assertEqual([str(self.cycle4.id), str(self.cycle3.id), str(self.cycle1.id)], list(office['cycles_by_id'].keys()))
        # self.assertEqual([str(self.cycle4.id), str(self.cycle3.id), str(self.cycle1.id)], list(retail['cycles_by_id'].keys()))

        # self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_default_field'], list(office['cycles_by_id'][str(self.cycle1.id)]))
        # self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_default_field'], list(office['cycles_by_id'][str(self.cycle4.id)]))
        # self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_default_field'], list(retail['cycles_by_id'][str(self.cycle1.id)]))
        # self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_default_field'], list(retail['cycles_by_id'][str(self.cycle4.id)]))

        # office_cycle1 = office['cycles_by_id'][str(self.cycle1.id)]
        # office_cycle4 = office['cycles_by_id'][str(self.cycle4.id)]

        # self.assertEqual(10, office_cycle1['Average'])
        # self.assertEqual(1, office_cycle1['Count'])
        # self.assertEqual(10, office_cycle1['Maximum'])
        # self.assertEqual(10, office_cycle1['Minimum'])
        # self.assertEqual(10, office_cycle1['Sum'])
        # exp = {self.view10.state.address_line_1: 10.0}
        # self.assertEqual(exp, office_cycle1['views_by_default_field'])

        # self.assertEqual(None, office_cycle4['Average'])
        # self.assertEqual(0, office_cycle4['Count'])
        # self.assertEqual(None, office_cycle4['Maximum'])
        # self.assertEqual(None, office_cycle4['Minimum'])
        # self.assertEqual(None, office_cycle4['Sum'])
        # self.assertEqual({}, office_cycle4['views_by_default_field'])

        # retail_cycle1 = retail['cycles_by_id'][str(self.cycle1.id)]
        # retail_cycle4 = retail['cycles_by_id'][str(self.cycle4.id)]

        # self.assertEqual(None, retail_cycle1['Average'])
        # self.assertEqual(0, retail_cycle1['Count'])
        # self.assertEqual(None, retail_cycle1['Maximum'])
        # self.assertEqual(None, retail_cycle1['Minimum'])
        # self.assertEqual(None, retail_cycle1['Sum'])
        # self.assertEqual({}, retail_cycle1['views_by_default_field'])

        # self.assertEqual(None, retail_cycle4['Average'])
        # self.assertEqual(0, retail_cycle4['Count'])
        # self.assertEqual(None, retail_cycle4['Maximum'])
        # self.assertEqual(None, retail_cycle4['Minimum'])
        # self.assertEqual(None, retail_cycle4['Sum'])
        # self.assertEqual({}, retail_cycle4['views_by_default_field'])

        # # check graph_data
        # self.assertEqual(['labels', 'datasets'], list(graph_data.keys()))
        # # 2 filter groups * 2 columns * 5 aggregation types
        # self.assertEqual(20, len(graph_data['datasets']))

        # avg_count = len([dataset for dataset in graph_data['datasets'] if dataset['aggregation'] == 'Average'])
        # max_count = len([dataset for dataset in graph_data['datasets'] if dataset['aggregation'] == 'Maximum'])
        # min_count = len([dataset for dataset in graph_data['datasets'] if dataset['aggregation'] == 'Minimum'])
        # sum_count = len([dataset for dataset in graph_data['datasets'] if dataset['aggregation'] == 'Sum'])
        # count_count = len([dataset for dataset in graph_data['datasets'] if dataset['aggregation'] == 'Count'])
        # self.assertEqual(4, avg_count)
        # self.assertEqual(4, max_count)
        # self.assertEqual(4, min_count)
        # self.assertEqual(4, sum_count)
        # self.assertEqual(4, count_count)

        # site_eui_count = len([dataset for dataset in graph_data['datasets'] if dataset['column'] == 'site_eui'])
        # ghg_count = len([dataset for dataset in graph_data['datasets'] if dataset['column'] == 'total_ghg_emissions'])
        # self.assertEqual(10, site_eui_count)
        # self.assertEqual(10, ghg_count)

        # office_count = len([dataset for dataset in graph_data['datasets'] if dataset['filter_group'] == 'office'])
        # retail_count = len([dataset for dataset in graph_data['datasets'] if dataset['filter_group'] == 'retail'])
        # self.assertEqual(10, office_count)
        # self.assertEqual(10, retail_count)

        # for dataset in graph_data['datasets']:
        #     self.assertEqual(3, len(dataset['data']))
