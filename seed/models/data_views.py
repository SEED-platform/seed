# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import logging

from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum
from django.http import QueryDict

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.models.properties import PropertyState, PropertyView
from seed.utils.search import build_view_filters_and_sorts


class DataView(models.Model):
    name = models.CharField(max_length=255, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    cycles = models.ManyToManyField(Cycle)
    filter_groups = models.JSONField()


    def evaluate(self):
        response = {
            'meta': {
                'organization': self.organization.id,
                'data_view': self.id,
            },
            'filter_group_view_ids':{},
            'data': {}
        }
        response, views_by_filter = self._views_by_filter(response)

        # assign data based on source column name
        for parameter in self.parameters.all():
            data = response['data']
            column_name = parameter.column.column_name
            data[column_name] = {'filter_groups': {}, 'unit': None}

            # self._assign_data_based_on_filter_groups(data, column_name, views_by_filter, parameter)
            for filter_group in self.filter_groups:
                filter_name = filter_group['name']
                data[column_name]['filter_groups'][filter_name] = {}

                # each filter group will contain list[dict] for each aggregation type and disaggregated property views values by view id
                # and disaggregated property views values by view id
                for aggregation in [Avg, Max, Min, Sum, Count, 'views_by_id']:
                    self._format_filter_group_data(data, column_name, filter_name, aggregation)

                    for cycle in self.cycles.all():
                        views = views_by_filter[filter_name][cycle.name]
                        states = PropertyState.objects.filter(propertyview__in=views)

                        # view_id: [{'cycle': cycle.name, 'value': value}]
                        if aggregation == 'views_by_id':
                            for view in views:
                                # Default assignment on first pass
                                data[column_name]['filter_groups'][filter_name][aggregation][view.id] = data[column_name]['filter_groups'][filter_name][aggregation].get(view.id, [])
                                state_data, unit = self._format_view_state_data(cycle, parameter, view)

                                if not data[column_name].get('unit'):
                                    data[column_name]['unit'] = unit

                                data[column_name]['filter_groups'][filter_name][aggregation][view.id].append(state_data)

                        # aggregation_type: {'cycle': cycle.name, 'value': value}
                        else:
                            value = self._evaluate_aggregation(states, aggregation, parameter.column)
                            value_dict = {'cycle': cycle.name, 'value': value}
                            data[column_name]['filter_groups'][filter_name][aggregation.name].append(value_dict)

        return response


    def _format_filter_group_data(self, data, column_name, filter_name, aggregation):
        if aggregation == 'views_by_id':
            data[column_name]['filter_groups'][filter_name][aggregation] = {}
        else :
            data[column_name]['filter_groups'][filter_name][aggregation.name] = []


    def _format_view_state_data(self, cycle, parameter, view):
        state_data = {'cycle': cycle.name}

        if parameter.column.is_extra_data:
            value = view.state.extra_data[parameter.column.column_name]
        elif parameter.column.derived_column:
            value = parameter.column.derived_column.evaluate(view.state)
        else:
            value = getattr(view.state, parameter.column.column_name)

        if isinstance(value, (str, int, float, bool)):
            state_data['value'] = value
            unit = None
        else:
            state_data['value'] = round(value.m, 2)
            unit = '{:P~}'.format(value.u)

        return state_data, unit


    def _evaluate_aggregation(self, states, aggregation, column):
        if column.is_extra_data:
            return self._evaluate_extra_data(states, aggregation, column)
        elif column.derived_column:
            return self._evaluate_derived_column(states, aggregation, column)
        else:
            aggregation = states.aggregate(value=aggregation(column.column_name))

            if aggregation.get('value') or aggregation.get('value') == 0:
                value = aggregation['value']
                if type(value) is int or type(value) is float:
                    return round(value, 2)
                return round(value.m, 2)


    def _evaluate_extra_data(self, states, aggregation, column):
        extra_data_col = 'extra_data__' + column.column_name
        q_set = states.values(extra_data_col)
        values = []
        for val in list(q_set):
            try:
                values.append(float(val[extra_data_col]))
            except (ValueError, TypeError):
                pass
        if values:
            type_to_aggregate = {Avg: sum(values) / len(values), Count: len(values), Max: max(values), Min: min(values), Sum: sum(values)}
            return round(type_to_aggregate[aggregation], 2)

    def _evaluate_derived_column(self, states, aggregation, column):
        # to evluate a derived_column: DerivedColumn.evaluate(propertyState)
        values = []

        for state in states:
            val = column.derived_column.evaluate(state)
            if val is not None:
                values.append(val)

        if values:
            type_to_aggregate = {Avg: sum(values) / len(values), Count: len(values), Max: max(values), Min: min(values), Sum: sum(values)}
            return  round(type_to_aggregate[aggregation], 2)


    def _get_filter_group_views(self, cycle, query_dict):
        org_id = self.organization.id
        columns = Column.retrieve_all(
            org_id=org_id,
            inventory_type='property',
            only_used=False,
            include_related=False
        )
        annotations=''
        try:
            filters, annotations, order_by = build_view_filters_and_sorts(query_dict, columns)

        except:
            logging.error('error with filter group')

        views_list = (
                PropertyView.objects.select_related('property', 'state', 'cycle')
                .filter(property__organization_id=org_id, cycle=cycle)
            )

        views_list = views_list.annotate(**annotations).filter(filters).order_by(*order_by)
        return views_list


    def _views_by_filter(self, response):
        views_by_filter = {}
        for filter_group in self.filter_groups:
            response['filter_group_view_ids'][filter_group['name']] = {}
            query_dict = QueryDict(mutable=True)
            query_dict.update(filter_group['query_dict'])
            views_by_filter[filter_group['name']] = {}
            for cycle in self.cycles.all():
                views = self._get_filter_group_views(cycle, query_dict)
                views_by_filter[filter_group['name']][cycle.name] = views
                response['filter_group_view_ids'][filter_group['name']][cycle.name] = [view['id'] for view in list(views.values('id'))]

        return response, views_by_filter


class DataViewParameter(models.Model):
    data_view = models.ForeignKey(DataView, on_delete=models.CASCADE, related_name='parameters')
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    location = models.CharField(max_length=255)
    aggregations = models.JSONField()
    # target field is undetermined, this is a stand in
    target = models.CharField(max_length=255, blank=True)
