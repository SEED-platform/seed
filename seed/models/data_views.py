# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import pty
from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models import Column, Cycle, DataAggregation, data_aggregations, PropertyState


class DataView(models.Model):
    name = models.CharField(max_length=255, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    filter_group = models.JSONField()
    cycles = models.ManyToManyField(Cycle)
    columns = models.ManyToManyField(Column)
    data_aggregations = models.ManyToManyField(DataAggregation)

    def evaluate(self):
        columns = self.columns.all()
        cycles = self.cycles.all()
        data_aggregations = self.data_aggregations.all()
        filter_group = self.filter_group 
        # filter group is not built out yet, for now, use all propertyview.states on the cycle

        response = {
            'meta': {
                'organization': self.organization.id,
                'data_view': self.id,
            },
            'data': {}
            }

        data = response['data']
        for cycle in cycles:
            end_date = cycle.end.strftime("%Y-%m-%d")
            data[end_date] = {}
            states = PropertyState.objects.filter(propertyview__in=cycle.propertyview_set.all())
            
            for column in columns:
                data[end_date][column.column_name] = {'views_by_id': {}}
                for state in states: 
                    if not data[end_date][column.column_name].get('units'):
                        data[end_date][column.column_name]['units'] = "{:P~}".format(getattr(state, column.column_name).u)
                    breakpoint()
                    data[end_date][column.column_name]['views_by_id'][state.propertyview_set.first().id] = getattr(state, column.column_name).m

                for data_agg in [data_agg for data_agg in data_aggregations if data_agg.column == column]:
                    data[end_date][column.column_name][data_agg.name] = data_agg.evaluate(states)

        return response

        # expected output 
        # output = {
        #     cylce1.end : {
        #         source_column1 = {
        #           column_name: 'site eui',
        #           units: 'kbtu/ft2/year'
        #           data_aggregation1 = 10,
        #           prop1 = 1,
        #           prop2 = 2,
        #           prop3 = 3
        #         }
        #     },
        #     cylce2 : {...},
        #     cylce3 : {...},
        # }