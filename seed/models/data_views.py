# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import pty
import logging
from django.db import models


from seed.lib.superperms.orgs.models import Organization
from seed.models.cycles import Cycle
from seed.models.columns import Column
from seed.models.properties import PropertyState, PropertyView
from django.db.models import Avg, Count, Max, Min, Sum
from django.http import QueryDict


# This causes a circular import.
from seed.utils.search import build_view_filters_and_sorts
# Work around: passing build_view_filters_and_sorts as an argument from views/v3/data_views




class DataView(models.Model):
    name = models.CharField(max_length=255, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    cycles = models.ManyToManyField(Cycle)
    filter_groups = models.JSONField()

    def get_filter_group_views(self, cycle, query_dict):
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

    def views_by_filter(self, response):
        views_by_filter = {}
        for filter_group in self.filter_groups:
            response['filter_group_view_ids'][filter_group['name']] = {}
            query_dict = QueryDict(mutable=True)
            query_dict.update(filter_group['query_dict'])
            views_by_filter[filter_group['name']] = {}
            for cycle in self.cycles.all():
                views = self.get_filter_group_views(cycle, query_dict)
                views_by_filter[filter_group['name']][cycle.name] = views
                response['filter_group_view_ids'][filter_group['name']][cycle.name] = [view['id'] for view in list(views.values('id'))]
        
        return response, views_by_filter


    def evaluate(self):
        response = {
            'meta': {
                'organization': self.organization.id,
                'data_view': self.id,
            },
            'filter_group_view_ids':{},
            'data': {}
        }
        response, views_by_filter = self.views_by_filter(response)


        # assign data based on source column name
        for parameter in self.parameters.all():
            data = response['data']
            column_name = parameter.column.column_name
            data[column_name] = {
                'filter_groups': {}
            }

            # assign data based on filter_groups
            for filter_group in self.filter_groups:
                filter_name = filter_group['name']
                data[column_name]['filter_groups'][filter_name] = {}

                # each filter group will contain list[dict] for each aggregation type and disaggregated property views values by view id
                # and disaggregated property views values by view id
                for aggregation in [Avg, Max, Min, Sum, Count, 'views_by_id']:
                    if aggregation == 'views_by_id':
                        data[column_name]['filter_groups'][filter_name][aggregation] = {}
                    else :
                        data[column_name]['filter_groups'][filter_name][aggregation.name] = []
    
                    for cycle in self.cycles.all():
                        views = views_by_filter[filter_name][cycle.name]
                        states = PropertyState.objects.filter(propertyview__in=views)

                        self.assign_aggregation_dicts(aggregation, views, data, column_name, filter_name, cycle, parameter, states)

                        # view_id: [{'cycle': cycle.name, 'value': value}]       
                        # if aggregation == 'views_by_id':
                        #     for view in views:
                        #         data[column_name]['filter_groups'][filter_name][aggregation][view.id] = data[column_name]['filter_groups'][filter_name][aggregation].get(view.id, [])
                        #         state_dict = state_dict = {'cycle': cycle.name}
                        #         if parameter.column.is_extra_data:
                        #             value = view.state.extra_data[parameter.column.column_name]
                        #         else:
                        #             value = getattr(view.state, parameter.column.column_name)

                        #         if type(value) == str or type(value) == int:
                        #            state_dict['value'] = value
                        #         else:
                        #             state_dict['value'] = round(value.m, 2)
                        #             data[column_name]['unit'] = data[column_name].get('unit', '{:P~}'.format(value.u))

                        #         data[column_name]['filter_groups'][filter_name][aggregation][view.id].append(state_dict)
                                
                        # # each dict: aggregation_type: {'cycle': cycle.name, 'value': value}
                        # else: 
                        #     value = self.evaluate_aggregation(states, aggregation, parameter.column)
                        #     value_dict = {'cycle': cycle.name, 'value': value}
                        #     data[column_name]['filter_groups'][filter_name][aggregation.name].append(value_dict)

        return response

    # given a cycle and aggregation, return the cycle name and its associated aggregation value
    def assign_aggregation_dicts(self, aggregation, views, data, column_name, filter_name, cycle, parameter, states):
        # view_id: [{'cycle': cycle.name, 'value': value}]       
        if aggregation == 'views_by_id':
            for view in views:
                data[column_name]['filter_groups'][filter_name][aggregation][view.id] = data[column_name]['filter_groups'][filter_name][aggregation].get(view.id, [])
                state_dict = state_dict = {'cycle': cycle.name}
                if parameter.column.is_extra_data:
                    value = view.state.extra_data[parameter.column.column_name]
                else:
                    value = getattr(view.state, parameter.column.column_name)

                if type(value) == str or type(value) == int:
                    state_dict['value'] = value
                else:
                    state_dict['value'] = round(value.m, 2)
                    data[column_name]['unit'] = data[column_name].get('unit', '{:P~}'.format(value.u))

                data[column_name]['filter_groups'][filter_name][aggregation][view.id].append(state_dict)
                
        # each dict: aggregation_type: {'cycle': cycle.name, 'value': value}
        else: 
            value = self.evaluate_aggregation(states, aggregation, parameter.column)
            value_dict = {'cycle': cycle.name, 'value': value}
            data[column_name]['filter_groups'][filter_name][aggregation.name].append(value_dict)




    def evaluate_aggregation(self, states, aggregation, column):

        if column.is_extra_data:
            return self.evaluate_extra_data(states, aggregation, column)
        elif column.derived_column:
            return self.evaluate_derived_column(states)
        else:
            aggregation = states.aggregate(value=aggregation(column.column_name))

            if aggregation.get('value') or aggregation.get('value') == 0:
                value = aggregation['value']
                if type(value) is int or type(value) is float:
                    return round(value, 2)
                return round(value.m, 2)

    def evaluate_extra_data(self, states, aggregation, column):
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

    def evaluate_derived_column(self, states):
        # to evluate a derived_column: DerivedColumn.evaluate(propertyState)
        property_states = states
        # property_states = PropertyState.objects.filter(organization=self.organization.id, propertyview__isnull=False)
        values = []

        for state in property_states:
            val = self.column.derived_column.evaluate(state)
            if val is not None:
                values.append(val)

        if values:
            type_to_aggregate = {0: sum(values) / len(values), 1: len(values), 2: max(values), 3: min(values), 4: sum(values)}
            return {"value": round(type_to_aggregate[self.type], 2)}
            # return {"value": round(type_to_aggregate[self.type], 2), "units": None}

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

class DataViewParameter(models.Model):
    data_view = models.ForeignKey(DataView, on_delete=models.CASCADE, related_name='parameters')
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    location = models.CharField(max_length=255)
    aggregations = models.JSONField()
    # target field is undetermined, this is a stand in
    target = models.CharField(max_length=255, blank=True)