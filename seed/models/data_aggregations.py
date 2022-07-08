# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum

from seed.lib.superperms.orgs.models import Organization
from seed.models import Column, PropertyState


class DataAggregation(models.Model):
    name = models.CharField(max_length=255)
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    AVG = 0
    COUNT = 1
    MAX = 2
    MIN = 3
    SUM = 4
    AGGREGATION_TYPES = (
        (AVG, 'Average'),
        (COUNT, 'Count'),
        (MAX, 'Max'),
        (MIN, 'Min'),
        (SUM, 'Sum'),
    )

    type = models.IntegerField(choices=AGGREGATION_TYPES)

    def evaluate(self):
        column = self.column

        if column.is_extra_data:
            return self.evaluate_extra_data()
        elif column.derived_column:
            return self.evaluate_derived_column()
        else:
            type_lookup = {0: Avg, 1: Count, 2: Max, 3: Min, 4: Sum}
            # PropertyState must be associated with the current org and a valid PropertyView
            aggregation = PropertyState.objects.filter(organization=self.organization.id, propertyview__isnull=False).aggregate(value=type_lookup[self.type](column.column_name))

            if aggregation.get('value') or aggregation.get('value') == 0:
                value = aggregation['value']
                if type(value) is int or type(value) is float:
                    return {"value": round(value, 2), "units": None}

                return {"value": round(value.m, 2), "units": "{:P~}".format(value.u)}

    def evaluate_extra_data(self):
        extra_data_col = 'extra_data__' + self.column.column_name
        q_set = PropertyState.objects.filter(organization=self.organization.id, propertyview__isnull=False).values(extra_data_col)
        values = []
        for val in list(q_set):
            try:
                values.append(float(val[extra_data_col]))
            except (ValueError, TypeError):
                pass

        if values:
            type_to_aggregate = {0: sum(values) / len(values), 1: len(values), 2: max(values), 3: min(values), 4: sum(values)}
            return {"value": round(type_to_aggregate[self.type], 2), "units": None}

    def evaluate_derived_column(self):
        # to evluate a derived_column: DerivedColumn.evaluate(propertyState)
        property_states = PropertyState.objects.filter(organization=self.organization.id, propertyview__isnull=False)
        values = []

        for state in property_states:
            val = self.column.derived_column.evaluate(state)
            if val is not None:
                values.append(val)

        if values:
            type_to_aggregate = {0: sum(values) / len(values), 1: len(values), 2: max(values), 3: min(values), 4: sum(values)}
            return {"value": round(type_to_aggregate[self.type], 2), "units": None}
