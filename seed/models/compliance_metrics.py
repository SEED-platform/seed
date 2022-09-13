# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
"""

from datetime import datetime

from django.db import models
from django.utils import timezone

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.utils.properties import properties_across_cycles


class ComplianceMetric(models.Model):

    TARGET_GT_ACTUAL = 0  # example: GHG, Site EUI
    TARGET_LT_ACTUAL = 1  # example: EnergyStar Score
    METRIC_TYPES = (
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
        return 'Compliance Metric - %s' % self.name

    # TODO finish this
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
        # needed?
        response['cycles'] = list(cycles.values('id', 'name'))

        # which column IDs to retrieve?
        # metric_columns = list(self.x_axis_columns.all())
        # for c in [self.actual_energy_column, self.target_energy_column, self.actual_emission_column, self.target_emission_column]:
        #     if c is not None:
        #         metric_columns.append(c)

        # print(f"~!!!!!!!! METRIC COLUMN IDS:{metric_columns}")
        # column_ids = [ sub.id for sub in metric_columns ]
        # print(f"COLUMN IDS: {column_ids}")

        # get properties
        property_response = properties_across_cycles(self.organization_id, -1, cycle_ids)
        # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # print(property_response)

        datasets = {'y': {'data': [], 'label': 'compliant'}, 'n': {'data': [], 'label': 'non-compliant'}, 'u': {'data': [], 'label': 'unknown'}}
        results_by_cycles = {}
        # figure out what kind of metric it is (energy? emission? combo? bool?)
        energy_bool = False
        emission_bool = False
        energy_metric = False
        emission_metric = False

        if self.actual_energy_column is not None:
            energy_metric = True
            if self.target_energy_column is None:
                energy_bool = True

        if self.actual_emission_column is not None:
            emission_metric = True
            if self.target_emission_column is None:
                emission_bool = True

        for cyc in property_response:

            # print(f" CYCLE? {cyc}")
            properties = {}
            cnts = {'y': 0, 'n': 0, 'u': 0}

            for p in property_response[cyc]:
                # initialize
                properties[p['property_view_id']] = None
                # energy metric
                if energy_metric:
                    properties[p['property_view_id']] = self._calculate_compliance(p, energy_bool, 'energy')
                # emission metric
                if emission_metric and properties[p['property_view_id']] != 'u':
                    temp_val = self._calculate_compliance(p, emission_bool, 'emission')

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

            # print(f"COUNTS: {cnts}")

            # reshape and save
            results_by_cycles[cyc] = {}
            for key in cnts:
                results_by_cycles[cyc][key] = [i for i in properties if properties[i] == key]

        # save to response
        response['results_by_cycles'] = results_by_cycles
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
        if the_type == 0:
            differential = target_val - actual_val
        else:
            differential = actual_val - target_val

        return 'y' if differential > 0 else 'n'

    # retrieves column data by id substring
    def _get_column_data(self, data, substring):
        value = next(v for (k, v) in data.items() if k.endswith('_' + str(substring)))
        # print(f"value found for column ID {substring}: {value}")
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

    # temporary until we have the metric setup page
    @classmethod
    def get_or_create_default(cls, organization):
        metric = "default compliance metric"
        # metric = ComplianceMetric.objects.filter(organization=organization).first()
        # if not metric:
        #     name = 'Combined Site EUI and GHG Emissions Compliance'
        #     # TODO: make this more foolproof if these columns don't exist
        #     actual_column = Column.objects.filter(column_name='site_eui', organization=organization).first()
        #     target_column = Column.objects.filter(column_name='Target Site EUI', organization=organization).first()
        #     actual_emission_column = Column.objects.filter(column_name='total_ghg_emissions', organization=organization).first()
        #     target_emission_column = Column.objects.filter(column_name='Target Total GHG Emissions', organization=organization).first()
        #     x_axes = Column.objects.filter(column_name__in=['Year Built', 'Property Type', 'Conditioned Floor Area'], organization=organization).all()

        #     # TODO: use of tzinfo does some weird stuff here and changes the year at the extremes...
        #     # saving as 2,2 since we don't care about day/month

        #     metric = ComplianceMetric.objects.create(
        #         name=name,
        #         organization=organization,
        #         start=datetime(2017, 1, 1, tzinfo=timezone.utc),
        #         end=datetime(2021, 12, 31, tzinfo=timezone.utc),
        #         actual_energy_column=actual_column,
        #         target_energy_column=target_column,
        #         energy_metric_type=0,
        #         actual_emission_column=actual_emission_column,
        #         target_emission_column=target_emission_column,
        #         emission_metric_type=0
        #     )
        #     metric.x_axis_columns.set(x_axes)

        return metric
