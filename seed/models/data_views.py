# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import contextlib
import logging

from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum
from django.http import QueryDict

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.models.filter_group import FilterGroup
from seed.models.properties import PropertyState, PropertyView
from seed.utils.search import build_view_filters_and_sorts


class DataView(models.Model):
    name = models.CharField(max_length=255, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    cycles = models.ManyToManyField(Cycle)
    filter_groups = models.ManyToManyField(FilterGroup)

    def get_inventory(self, user_ali):
        views_by_filter_group_id, _ = self.views_by_filter(user_ali)
        return views_by_filter_group_id

    def views_by_filter(self, user_ali):
        filter_group_views = {}
        views_by_filter_group_id = {}
        for filter_group in self.filter_groups.all():
            views_by_filter_group_id[filter_group.id] = {}
            filter_group_views[filter_group.id] = {}
            query_dict = QueryDict(mutable=True)
            query_dict.update(filter_group.query_dict)
            for cycle in self.cycles.all():
                filter_views = self._get_filter_group_views(cycle, query_dict, user_ali)
                label_views = self._get_label_views(cycle, filter_group, user_ali)
                views = self._combine_views(filter_views, label_views)
                filter_group_views[filter_group.id][cycle.id] = views
                for view in views:
                    view_name = self._format_property_display_field(view)
                    views_by_filter_group_id[filter_group.id][view.id] = view_name

        return views_by_filter_group_id, filter_group_views

    def evaluate(self, columns, user_ali):
        # RETURN VALUE STRUCTURE

        # meta: {data_view: data_view.id, organization: organization.id},
        # views_by_filter_group_id: {
        #   filter_group.id: [
        #       view.state.default_field || state.id,
        #       view.state.default_field || state.id,
        #       ...
        #   ]
        # },
        # columns_by_id: {
        #   column.id: {
        #       filter_groups_by_id: {
        #           filer_group.id: {
        #               cycles_by_id: {
        #                   cycle.id: {
        #                       'Average': 123,
        #                       'Count': 123,
        #                       'Maximum': 123,
        #                       'Minimum': 123,
        #                       'Sum': 123,
        #                       'views_by_default_field: {
        #                           view.state.default_field || state.id: 123,
        #                           view.state.default_field || state.id: 123,
        #                           ...
        #                        }
        #                   }
        #               }
        #           }
        #       }
        #   }
        # },
        # graph_data: {
        #   labels = [cycle1.name, cycle2.name, cycle3.name, ...],
        #   datasets = [
        #       {filter_group: filter_group.name, column: column.column_name, aggregation: aggregation.name, data: [cycle1_value, cycle2_value, cycle3_value]},
        #       {filter_group: filter_group.name, column: column.column_name, aggregation: aggregation.name, data: [cycle1_value, cycle2_value, cycle3_value]},
        #       ...
        #   ]
        # }

        response = {
            'meta': {
                'organization': self.organization.id,
                'data_view': self.id,
            },
            'views_by_filter_group_id': {},
            'columns_by_id': {},
            'graph_data': {'labels': [cycle.name for cycle in sorted(self.cycles.all(), key=lambda x: x.name)], 'datasets': []},
        }

        response['views_by_filter_group_id'], views_by_filter = self.views_by_filter(user_ali)

        # assign data based on source column id
        for column in columns:
            data = response['columns_by_id']
            column_id = column.id
            data[column_id] = {'filter_groups_by_id': {}, 'unit': None}

            for filter_group in self.filter_groups.all():
                filter_id = filter_group.id
                data[column_id]['filter_groups_by_id'][filter_id] = {'cycles_by_id': {}}

                for cycle in self.cycles.all():
                    data_cycles = data[column_id]['filter_groups_by_id'][filter_id]['cycles_by_id']
                    data_cycles[cycle.id] = {}
                    views = views_by_filter[filter_id][cycle.id]
                    states = PropertyState.objects.filter(propertyview__in=views)

                    for aggregation in [Avg, Max, Min, Sum, Count, 'views_by_default_field']:
                        self._format_aggregation_name(aggregation)
                        self._format_filter_group_data(data_cycles, cycle.id, aggregation)

                        if aggregation == 'views_by_default_field':
                            self._assign_views_by_default_field_values(views, data, data_cycles, column, cycle.id, aggregation)
                        else:
                            value = self._evaluate_aggregation(states, aggregation, column)
                            data_cycles[cycle.id][aggregation.name] = value

        self._format_graph_data(response, columns, views_by_filter)
        return response

    def _format_graph_data(self, response, columns, views_by_filter):
        # {filter_group: filter_group.name, column: column.column_name, aggregation: aggregation.name, data: [1,2,3]},
        for filter_group in self.filter_groups.all():
            filter_id = filter_group.id
            filter_name = filter_group.name
            for column in columns:
                for aggregation in [Avg, Max, Min, Sum, Count]:  # NEED TO ADD 'views_by_label' for scatter plot
                    self._format_aggregation_name(aggregation)
                    dataset = {'data': [], 'column': column.display_name, 'aggregation': aggregation.name, 'filter_group': filter_name}
                    for cycle in sorted(self.cycles.all(), key=lambda x: x.name):
                        views = views_by_filter[filter_id][cycle.id]
                        states = PropertyState.objects.filter(propertyview__in=views)
                        value = self._evaluate_aggregation(states, aggregation, column)
                        dataset['data'].append(value)
                    response['graph_data']['datasets'].append(dataset)

    def _format_property_display_field(self, view):
        try:
            return getattr(view.state, self.organization.property_display_field)
        except AttributeError:
            return view.id

    def _format_aggregation_name(self, aggregation):
        if aggregation == Avg:
            aggregation.name = 'Average'
        elif aggregation == Max:
            aggregation.name = 'Maximum'
        elif aggregation == Min:
            aggregation.name = 'Minimum'

    def _assign_views_by_default_field_values(
        self,
        views,
        data,
        data_cycles,
        column,
        cycle_id,
        aggregation,
    ):
        for view in views:
            # Default assignment on first pass
            view_key = self._format_property_display_field(view)
            data_cycles[cycle_id][aggregation][view_key] = data_cycles[cycle_id][aggregation].get(view_key, [])

            if column.is_extra_data:
                state_value = view.state.extra_data.get(column.column_name)
            elif column.derived_column:
                state_value = column.derived_column.evaluate(view.state)
            else:
                state_value = getattr(view.state, column.column_name)

            try:
                value = round(state_value.m, 2)
                unit = f'{state_value.u:P~}'
            except AttributeError:
                value = state_value
                unit = None

            if not data[column.id].get('unit'):
                data[column.id]['unit'] = unit

            view_key = self._format_property_display_field(view)
            data_cycles[cycle_id][aggregation][view_key] = value

    def _format_filter_group_data(self, data_cycles, cycle_id, aggregation):
        if aggregation == 'views_by_default_field':
            data_cycles[cycle_id][aggregation] = {}
        else:
            data_cycles[cycle_id][aggregation.name] = []

    def _evaluate_aggregation(self, states, aggregation, column):
        if column.is_extra_data:
            return self._evaluate_extra_data(states, aggregation, column)
        elif column.derived_column:
            return self._evaluate_derived_column(states, aggregation, column)
        else:
            aggregation = states.aggregate(value=aggregation(column.column_name))

            if aggregation.get('value') or aggregation.get('value') == 0:
                value = aggregation['value']
                if isinstance(value, (float, int)):
                    return round(value, 2)
                return round(value.m, 2)

    def _evaluate_extra_data(self, states, aggregation, column):
        extra_data_col = 'extra_data__' + column.column_name
        q_set = states.values(extra_data_col)
        values = []
        for val in list(q_set):
            with contextlib.suppress(ValueError, TypeError):
                values.append(float(val[extra_data_col]))
        if values:
            type_to_aggregate = {Avg: sum(values) / len(values), Count: len(values), Max: max(values), Min: min(values), Sum: sum(values)}
            return round(type_to_aggregate[aggregation], 2)

    def _evaluate_derived_column(self, states, aggregation, column):
        # to evaluate a derived_column: DerivedColumn.evaluate(propertyState)
        values = []

        for state in states:
            val = column.derived_column.evaluate(state)
            if val is not None:
                values.append(val)

        if values:
            type_to_aggregate = {Avg: sum(values) / len(values), Count: len(values), Max: max(values), Min: min(values), Sum: sum(values)}
            return round(type_to_aggregate[aggregation], 2)

    def _combine_views(self, filter_views, label_views):
        if label_views or label_views == []:
            return list(set.intersection(*map(set, [label_views, filter_views])))
        else:
            return list(filter_views)

    def _get_label_views(self, cycle, filter_group, user_ali):
        if not (filter_group.and_labels.exists() or filter_group.or_labels.exists() or filter_group.exclude_labels.exists()):
            return None

        permissions_filter = {
            'property__access_level_instance__lft__gte': user_ali.lft,
            'property__access_level_instance__rgt__lte': user_ali.rgt,
        }

        and_labels = filter_group.and_labels.all()
        or_labels = filter_group.or_labels.all()
        exclude_labels = filter_group.exclude_labels.all()
        views = None

        if and_labels.exists():  # and
            views = views or cycle.propertyview_set.filter(**permissions_filter)
            for label in and_labels:
                views = views.filter(labels=label)
        if or_labels.exists():  # or
            views = views or cycle.propertyview_set.filter(**permissions_filter)
            views = views.filter(labels__in=or_labels)
        if exclude_labels.exists():  # exclude
            views = views or cycle.propertyview_set.filter(**permissions_filter)
            views = views.exclude(labels__in=exclude_labels)
        return list(views)

    def _get_filter_group_views(self, cycle, query_dict, user_ali):
        org_id = self.organization.id
        columns = Column.retrieve_all(org_id=org_id, inventory_type='property', only_used=False, include_related=False)
        annotations = {}
        try:
            filters, annotations, order_by = build_view_filters_and_sorts(query_dict, columns, 'property')
        except Exception:
            logging.error('error with filter group')

        views_list = PropertyView.objects.select_related('property', 'state', 'cycle').filter(
            property__organization_id=org_id,
            cycle=cycle,
            property__access_level_instance__lft__gte=user_ali.lft,
            property__access_level_instance__rgt__lte=user_ali.rgt,
        )

        views_list = views_list.annotate(**annotations).filter(filters).order_by(*order_by)
        return views_list


class DataViewParameter(models.Model):
    data_view = models.ForeignKey(DataView, on_delete=models.CASCADE, related_name='parameters')
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    location = models.CharField(max_length=255)
    aggregations = models.JSONField(blank=True)
    # target field is undetermined, this is a stand in
    target = models.CharField(max_length=255, blank=True)
