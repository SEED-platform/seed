# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from collections import defaultdict

from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework import status

from seed.decorators import (
    DecoratorMixin,
)

from seed.models import (
    PropertyView
)
from seed.utils.api import drf_api_endpoint
from seed.utils.generic import median, round_down_hundred_thousand


class Report(DecoratorMixin(drf_api_endpoint), ViewSet):
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get_raw_report_data(self, organization_id, cycles, x_var, y_var):
        all_property_views = PropertyView.objects.select_related(
            'property', 'state'
        ).filter(
            property__organization_id=organization_id,
            cycle_id__in=cycles
        )
        results = []
        for cycle in cycles:
            property_views = all_property_views.filter(cycle_id=cycle)
            count_total = []
            count_with_data = []
            data = []
            for property_view in property_views:
                # property.pk or taxlot.pk
                property_pk = property_view.property_pk
                state = property_view.state
                count_total.append(property_pk)
                if getattr(state, x_var, None) and getattr(state, y_var, None):
                    count_with_data.append(property_pk)
                    data.append({
                        "property_id": property_pk,
                        "x": getattr(state, x_var),
                        "y": getattr(state, y_var),
                    })
            assert(len(property_views) == len(set(count_total)))
            results.append[{
                "cycle": cycle,
                "num_properties": len(count_total),
                "num_properties_w-data": len(count_with_data),
                "data": data,
            }]
        return results

    def get_property_report_data(self):
        params = {}
        missing_params = []
        error = ''
        valid_values = [
            'site_eui', 'source_eui', 'site_eui_weather_normalized',
            'source_eui_weather_normalized', 'energy_score',
            'gross_floor_area', 'use_description', 'year_built'
        ]
        for param in ['x_var', 'y_var', 'organization_id']:
            val = self.request.query_params.get(param, None)
            if not val:
                missing_params.append(param)
            elif param in ['x_var', 'y_var'] and val not in valid_values:
                error = "{} {} is not a valid value for {}.".format(
                    error, val, param
                )
            else:
                params[param] = val
        cycles = self.request.query_params.getlist('cycle')
        if not cycles:
            missing_params.append('cycle')
        if missing_params:
            error = "{} Missing params: {}".format(
                error, ", ".join(missing_params)
            )
        if error:
            status_code = status.HTTP_400_BAD_REQUEST
            result = {'status': 'error', 'message': error}
        else:
            data = self.get_raw_report_data(
                self, params['organization_id'], cycles,
                params['x_var'], params['y_var']
            )
            empty = True
            for datum in data:
                if datum['num_properties_w-data'] != 0:
                    empty = False
                    break
            if empty:
                result = {'status': 'error', 'message': 'No data found'}
                status_code = status.HTTP_404_NOT_FOUND
            else:
                result = {'status': 'success', 'data': data}
                status_code = status.HTTP_200_OK
        return Response(result, status=status_code)

    def get_aggregated_property_report_data(self, request):
        valid_x_values = [
            'site_eui', 'source_eui', 'site_eui_weather_normalized',
            'source_eui_weather_normalized', 'energy_score',
        ]
        valid_y_values = ['gross_floor_area', 'use_description', 'year_built']
        params = {}
        missing_params = []
        error = ''
        for param in ['x_var', 'y_var', 'organization_id']:
            val = self.request.query_params.get(param, None)
            if not val:
                missing_params.append(param)
            elif param == 'x_var' and val not in valid_x_values:
                error = "{} {} is not a valid value for {}.".format(
                    error, val, param
                )
            elif param == 'y_var' and val not in valid_y_values:
                error = "{} {} is not a valid value for {}.".format(
                    error, val, param
                )
            else:
                params[param] = val
        cycles = self.request.query_params.getlist('cycle')
        if not cycles:
            missing_params.append('cycle')
        if missing_params:
            error = "{} Missing params: {}".format(
                error, ", ".join(missing_params)
            )
        params, cycles, error = self.get_params()
        if error:
            status_code = status.HTTP_400_BAD_REQUEST
            result = {'status': 'error', 'message': error}
        else:
            x_var = params['x_var']
            y_var = params['y_var']
            data = self.get_raw_report_data(
                self, params['organization_id'], cycles, x_var, y_var
            )
            empty = True
            for datum in data:
                if datum['num_properties_w-data'] != 0:
                    empty = False
                    break
            if empty:
                result = {'status': 'error', 'message': 'No data found'}
                status_code = status.HTTP_404_NOT_FOUND
            return Response(result, status=status_code)

            aggregated_data = []
            for datum in data:
                chart_data = []
                buildings = datum['data']
                if y_var == 'use_description':
                    chart_data = []
                    buildings = datum['data']
                    # Group buildings in this year_ending group into uses
                    grouped_uses = defaultdict(list)
                    for b in buildings:
                        if not getattr(b, y_var):
                            continue
                        grouped_uses[str(getattr(b, y_var)).lower()].append(b)

                    # Now iterate over use groups to make each chart item
                    for use, buildings_in_uses in grouped_uses.items():
                        chart_data.append({
                            'cycle': datum['cycle'],
                            'x': median([
                                getattr(b, x_var)
                                for b in buildings_in_uses if getattr(b, x_var)
                            ]),
                            'y': use.capitalize()
                        })

                elif y_var == 'year_built':
                    # Group buildings in this year_ending group into decades
                    grouped_decades = defaultdict(list)
                    for b in buildings:
                        if not getattr(b, y_var):
                            continue
                        grouped_decades['%s0' % str(getattr(b, y_var))[:-1]].append(b)

                    # Now iterate over decade groups to make each chart item
                    for decade, buildings_in_decade in grouped_decades.items():
                        chart_data.append({
                            'cycle': datum['cycle'],
                            'x': median([
                                getattr(b, x_var)
                                for b in buildings_in_decade if getattr(b, x_var)
                            ]),
                            'y': '%s-%s' % (decade, '%s9' % str(decade)[:-1])  # 1990-1999
                        })

                elif y_var == 'gross_floor_area':
                    y_display_map = {
                        0: '0-99k',
                        100000: '100-199k',
                        200000: '200k-299k',
                        300000: '300k-399k',
                        400000: '400-499k',
                        500000: '500-599k',
                        600000: '600-699k',
                        700000: '700-799k',
                        800000: '800-899k',
                        900000: '900-999k',
                        1000000: 'over 1,000k',
                    }
                    max_bin = max(y_display_map.keys())

                    # Group buildings in this year_ending group into ranges
                    grouped_ranges = defaultdict(list)
                    for b in buildings:
                        if not getattr(b, y_var):
                            continue
                        area = getattr(b, y_var)
                        # make sure anything greater than the biggest bin gets put in
                        # the biggest bin
                        range_bin = min(max_bin, round_down_hundred_thousand(area))
                        grouped_ranges[range_bin].append(b)

                    # Now iterate over range groups to make each chart item
                    for range_floor, buildings_in_range in grouped_ranges.items():
                        chart_data.append({
                            'cycle': datum['cycle'],
                            'x': median([
                                getattr(b, x_var)
                                for b in buildings_in_range if getattr(b, x_var)
                            ]),
                            'y': y_display_map[range_floor]
                        })

                aggregated_data.update({
                    'cycle': datum['cycle'],
                    'data': chart_data,
                    'num_properties': datum['num_properties'],
                    'num_properties_w-data': datum['num_properties_w-data'],
                })
        # Send back to client
        result = {
            'status': 'success',
            'aggregated_data': aggregated_data,
        }
        return Response(result, status=status_code)
