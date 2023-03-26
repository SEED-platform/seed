# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import numbers
from typing import Union

from django.db import models
from django.http import QueryDict

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.models.filter_group import FilterGroup
from seed.utils.properties import properties_across_cycles_with_filters


class ComplianceMetric(models.Model):

    TARGET_NONE = 0
    TARGET_GT_ACTUAL = 1  # example: GHG, Site EUI
    TARGET_LT_ACTUAL = 2  # example: EnergyStar Score
    METRIC_TYPES = (
        (TARGET_NONE, ''),
        (TARGET_GT_ACTUAL, 'Target > Actual for Compliance'),
        (TARGET_LT_ACTUAL, 'Target < Actual for Compliance'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='compliance_metrics', blank=True, null=True)
    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    # TODO: could these be derived columns?
    actual_energy_column = models.ForeignKey(Column, related_name="actual_energy_column", null=True, on_delete=models.CASCADE)
    target_energy_column = models.ForeignKey(Column, related_name="target_energy_column", null=True, on_delete=models.CASCADE)
    energy_metric_type = models.IntegerField(choices=METRIC_TYPES, blank=True, null=True)
    actual_emission_column = models.ForeignKey(Column, related_name="actual_emission_column", null=True, on_delete=models.CASCADE)
    target_emission_column = models.ForeignKey(Column, related_name="target_emission_column", null=True, on_delete=models.CASCADE)
    emission_metric_type = models.IntegerField(choices=METRIC_TYPES, blank=True, null=True)
    filter_group = models.ForeignKey(FilterGroup, related_name="filter_group", null=True, on_delete=models.CASCADE)
    x_axis_columns = models.ManyToManyField(Column, related_name="x_axis_columns", blank=True)
    cycles = models.ManyToManyField(Cycle, related_name="cycles", blank=True)

    def __str__(self):
        return 'Program Metric - %s' % self.name

    def evaluate(self):
        response = {
            'meta': {
                'organization': self.organization.id,
                'compliance_metric': self.id,
            },
            'name': self.name,
            'graph_data': {
                'labels': [],
                'datasets': []
            },
            'cycles': []
        }

        query_dict = QueryDict(mutable=True)
        if self.filter_group and self.filter_group.query_dict:
            query_dict.update(self.filter_group.query_dict)
        # print(f"query dict: {query_dict}")

        # grab cycles
        cycle_ids = self.cycles.values_list('pk', flat=True).order_by('start')
        response['graph_data']['labels'] = list(self.cycles.values_list('name', flat=True).order_by('start'))
        response['cycles'] = list(self.cycles.values('id', 'name'))

        # get properties (no filter)
        # property_response = properties_across_cycles(self.organization_id, -1, cycle_ids)
        # get properties (applies filter group)
        display_field_id = Column.objects.get(table_name="PropertyState", column_name=self.organization.property_display_field, organization=self.organization).id
        # array of columns to return
        column_ids = [
            display_field_id
        ]

        if self.actual_energy_column is not None:
            column_ids.append(self.actual_energy_column.id)
            if self.target_energy_column is not None:
                column_ids.append(self.target_energy_column.id)

        if self.actual_emission_column is not None:
            column_ids.append(self.actual_emission_column.id)
            if self.target_emission_column is not None:
                column_ids.append(self.target_emission_column.id)

        for col in self.x_axis_columns.all():
            column_ids.append(col.id)

        # Unique ids
        column_ids = [*set(column_ids)]

        property_response = properties_across_cycles_with_filters(
            self.organization_id,
            cycle_ids,
            query_dict,
            column_ids
        )

        datasets = {'y': {'data': [], 'label': 'compliant'}, 'n': {'data': [], 'label': 'non-compliant'}, 'u': {'data': [], 'label': 'unknown'}}
        results_by_cycles = {}
#        property_datasets = {}
        # figure out what kind of metric it is (energy? emission? combo? bool?)
        metric = {
            'energy_metric': False,
            'emission_metric': False,
            'energy_bool': False,
            'emission_bool': False,
            'actual_energy_column': None,
            'actual_energy_column_name': None,
            'target_energy_column': None,
            'energy_metric_type': self.energy_metric_type,
            'actual_emission_column': None,
            'actual_emission_column_name': None,
            'target_emission_column': None,
            'emission_metric_type': self.emission_metric_type,
            'filter_group': None,
            'cycles': list(self.cycles.all().values('id', 'name')),
            'x_axis_columns': list(self.x_axis_columns.all().values('id', 'display_name'))}

        if self.actual_energy_column is not None:
            metric['actual_energy_column'] = self.actual_energy_column.id
            metric['actual_energy_column_name'] = self.actual_energy_column.display_name
            metric['energy_metric'] = True
            if self.target_energy_column is None:
                metric['energy_bool'] = True
            else:
                metric['target_energy_column'] = self.target_energy_column.id

        if self.actual_emission_column is not None:
            metric['emission_metric'] = True
            metric['actual_emission_column'] = self.actual_emission_column.id
            metric['actual_emission_column_name'] = self.actual_emission_column.display_name
            if self.target_emission_column is None:
                metric['emission_bool'] = True
            else:
                metric['target_emission_column'] = self.target_emission_column.id

        for cyc in property_response:
            properties = {}
            cnts = {'y': 0, 'n': 0, 'u': 0}

            for p in property_response[cyc]:
                # initialize
                properties[p['property_view_id']] = None
                # energy metric
                if metric['energy_metric']:
                    properties[p['property_view_id']] = self._calculate_compliance(p, metric['energy_bool'], 'energy')
                # emission metric
                if metric['emission_metric'] and properties[p['property_view_id']] != 'u':
                    temp_val = self._calculate_compliance(p, metric['emission_bool'], 'emission')

                    # reconcile
                    if temp_val == 'u':
                        # unknown stays unknown (missing data)
                        properties[p['property_view_id']] = 'u'
                    elif properties[p['property_view_id']] is None:
                        # only emission metric (not energy metric)
                        properties[p['property_view_id']] = temp_val
                    else:
                        # compliant if both are compliant
                        properties[p['property_view_id']] = temp_val if temp_val == 'n' else properties[p['property_view_id']]

            # count compliant, non-compliant, unknown for each property with data
            for key in cnts:
                cnts[key] = sum(map((key).__eq__, properties.values()))
                # add to dataset
                datasets[key]['data'].append(cnts[key])

            # reshape and save
            results_by_cycles[cyc] = {}
            for key in cnts:
                results_by_cycles[cyc][key] = [i for i in properties if properties[i] == key]

        # save to response
        response['results_by_cycles'] = results_by_cycles
        response['properties_by_cycles'] = property_response
        response['metric'] = metric

        for key in datasets:
            response['graph_data']['datasets'].append(datasets[key])

        return response

    def _calculate_compliance(self, the_property, bool_metric, metric_type):
        """Return the compliant, non-compliant, and unknown counts

        Args:
            the_property (PropertyState): The property state object to check compliance
            bool_metric (Boolean): If the metric is a boolean metric, otherwise, it is a target metric
            metric_type (Int): Target > Actual or Target < Actual

        Returns:
            string: single character string representing compliance status, u - unknown, y - compliant, n - non-compliant
        """
        actual_col = self.actual_energy_column if metric_type == 'energy' else self.actual_emission_column
        target_col = self.target_energy_column if metric_type == 'energy' else self.target_emission_column
        actual_val = self._get_column_data(the_property, actual_col)
        if not isinstance(actual_val, numbers.Number):
            return 'u'

        if bool_metric:
            return 'y' if bool(actual_val) else 'n'

        target_val = self._get_column_data(the_property, target_col)
        if not isinstance(target_val, numbers.Number):
            return 'u'

        # test metric type
        the_type = self.energy_metric_type if metric_type == 'energy' else self.emission_metric_type
        # 1 = target is less than actual, 2 = target is greater than actual
        # TODO: convert int to enum types for readability
        if the_type == 1:
            differential = target_val - actual_val
        else:
            differential = actual_val - target_val

        return 'y' if differential >= 0 else 'n'

    def _get_column_data(self, data: dict, column: Column) -> Union[float, bool]:
        """Get the column datat from the dictionary version of the property state.
        Also, cast the datatype based on the column data_type as needed.

        Args:
            data (dict): property state dictionary
            column (Column): column object

        Returns:
            Union[float, bool]: the resulting value
        """
        # retrieves column data from the property state. The lookup is
        # based on the <column_name>_<column_id> format because the data
        # is the flat dictionary representation of the property state.
        column_lookup = f"{column.column_name}_{column.id}"
        value = data[column_lookup]

        # Now cast it based on the column data_type, this uses
        # the same method that is covered in the search.py file for
        # consistency
        return column.cast(value)

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
