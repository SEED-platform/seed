# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
"""


from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.utils.properties import properties_across_cycles


class ComplianceMetric(models.Model):

    TARGET_NONE = 0
    TARGET_GT_ACTUAL = 1  # example: GHG, Site EUI
    TARGET_LT_ACTUAL = 2  # example: EnergyStar Score
    METRIC_TYPES = (
        (TARGET_NONE, ''),
        (TARGET_GT_ACTUAL, 'Target > Actual for Compliance'),
        (TARGET_LT_ACTUAL, 'Actual > Target for Compliance'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='compliance_metrics', blank=True, null=True)
    name = models.CharField(max_length=255)
    start = models.DateTimeField()  # only care about year, but adding as a DateTime
    end = models.DateTimeField()  # only care about year, but adding as a DateTime
    created = models.DateTimeField(auto_now_add=True)
    # TODO: could these be derived columns?
    actual_energy_column = models.ForeignKey(Column, related_name="actual_energy_column", null=True, on_delete=models.CASCADE)
    target_energy_column = models.ForeignKey(Column, related_name="target_energy_column", null=True, on_delete=models.CASCADE)
    energy_metric_type = models.IntegerField(choices=METRIC_TYPES, blank=True, null=True)
    actual_emission_column = models.ForeignKey(Column, related_name="actual_emission_column", null=True, on_delete=models.CASCADE)
    target_emission_column = models.ForeignKey(Column, related_name="target_emission_column", null=True, on_delete=models.CASCADE)
    emission_metric_type = models.IntegerField(choices=METRIC_TYPES, blank=True, null=True)

    x_axis_columns = models.ManyToManyField(Column, related_name="x_axis_columns")

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

        # grab cycles within start and end dates
        cycles = Cycle.objects.filter(organization_id=self.organization.id, start__lte=self.end, end__gte=self.start).order_by('start')
        cycle_ids = cycles.values_list('pk', flat=True)
        response['graph_data']['labels'] = list(cycles.values_list('name', flat=True))
        response['cycles'] = list(cycles.values('id', 'name'))

        # get properties
        property_response = properties_across_cycles(self.organization_id, -1, cycle_ids)

        datasets = {'y': {'data': [], 'label': 'compliant'}, 'n': {'data': [], 'label': 'non-compliant'}, 'u': {'data': [], 'label': 'unknown'}}
        results_by_cycles = {}
#        property_datasets = {}
        # figure out what kind of metric it is (energy? emission? combo? bool?)
        metric = {'energy_metric': False, 'emission_metric': False, 'energy_bool': False, 'emission_bool': False,
                  'actual_energy_column': None, 'actual_energy_column_name': None, 'target_energy_column': None,
                  'energy_metric_type': self.energy_metric_type, 'actual_emission_column': None, 'actual_emission_column_name': None,
                  'target_emission_column': None, 'emission_metric_type': self.emission_metric_type,
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

    # returns compliant, non-compliant, and unknown counts
    def _calculate_compliance(self, the_property, bool_metric, metric_type):

        actual_col_id = self.actual_energy_column.id if metric_type == 'energy' else self.actual_emission_column.id
        target_col_id = self.target_energy_column.id if metric_type == 'energy' else self.target_emission_column.id

        actual_val = self._get_column_data(the_property, actual_col_id)
        if actual_val is None:
            return 'u'

        if bool_metric:
            return 'y' if actual_val > 0 else 'n'

        target_val = self._get_column_data(the_property, target_col_id)
        if target_val is None:
            return 'u'

        # test metric type
        the_type = self.energy_metric_type if metric_type == 'energy' else self.emission_metric_type
        if the_type == 1:
            differential = target_val - actual_val
        else:
            differential = actual_val - target_val

        return 'y' if differential >= 0 else 'n'

    # retrieves column data by id substring
    def _get_column_data(self, data, substring):
        value = next(v for (k, v) in data.items() if k.endswith('_' + str(substring)))
        return value

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

        constraints = [
            models.CheckConstraint(
                name="at_least_one_compliance_metric_type",
                check=(
                    models.Q(actual_energy_column__isnull=False)
                    | models.Q(actual_emission_column__isnull=False)

                ),
            )
        ]
