# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import csv
import re


from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    TaxLotProperty,
    PropertyView,
    TaxLotView

)
from seed.serializers.tax_lot_properties import (
    TaxLotPropertySerializer
)
from seed.utils.api import api_endpoint_class

INVENTORY_MODELS = {'properties': PropertyView, 'taxlots': TaxLotView}


class TaxLotPropertyViewSet(GenericViewSet):
    """
    The TaxLotProperty field is used to return the properties and tax lots from the join table.
    This method presently only works with the CSV, but should eventually be extended to be the
    viewset for any tax lot / property join API call.
    """
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotPropertySerializer

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['POST'])
    def csv(self, request):
        """
        Download a csv of the data quality checks by the pk which is the cache_key

        .. code-block::

            {
                    "ids": [1,2,3],
                    "columns": ["tax_jurisdiction_tax_lot_id", "address_line_1", "property_view_id"]
            }

        ---
        parameter_strategy: replace
        parameters:
            - name: cycle
              description: cycle
              required: true
              paramType: query
            - name: inventory_type
              description: properties or taxlots (as defined by the inventory list page)
              required: true
              paramType: query
            - name: ids
              description: list of property ids to export (not property views)
              required: true
              paramType: body
            - name: columns
              description: list of columns to export
              required: true
              paramType: body
            - name: filename
              description: name of the file to create
              required: false
              paramType: body


        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        columns = request.data.get('columns', None)
        if columns is None:
            # default the columns for now if no columns are passed
            columns = [
                'pm_property_id', 'pm_parent_property_id', 'tax_jurisdiction_tax_lot_id',
                'custom_id_1', 'tax_custom_id_1', 'city', 'state', 'postal_code',
                'tax_primary', 'property_name', 'campus', 'gross_floor_area',
                'use_description', 'energy_score', 'site_eui', 'property_notes',
                'property_type', 'year_ending', 'owner', 'owner_email', 'owner_telephone',
                'building_count', 'year_built', 'recent_sale_date', 'conditioned_floor_area',
                'occupied_floor_area', 'owner_address', 'owner_city_state', 'owner_postal_code',
                'home_energy_score_id', 'generation_date', 'release_date',
                'source_eui_weather_normalized', 'site_eui_weather_normalized', 'source_eui',
                'energy_alerts', 'space_alerts', 'building_certification', 'number_properties',
                'block_number', 'district', 'BLDGS', 'property_state_id', 'taxlot_state_id',
                'property_view_id', 'taxlot_view_id'
            ]

        # get the class to operate on and the relationships
        view_klass_str = request.query_params.get('inventory_type', 'properties')
        view_klass = INVENTORY_MODELS[view_klass_str]
        select_related = ['state', 'cycle']
        ids = request.data.get('ids', [])
        filter_str = {'cycle': cycle_pk}
        if hasattr(view_klass, 'property'):
            select_related.append('property')
            filter_str = {
                'property__organization_id': request.query_params['organization_id'],
            }
            if ids:
                filter_str['property__id__in'] = ids
            # always export the labels
            columns += ['property_labels']

        elif hasattr(view_klass, 'taxlot'):
            select_related.append('taxlot')
            filter_str = {
                'taxlot__organization_id': request.query_params['organization_id'],
            }
            if ids:
                filter_str['taxlot__id__in'] = ids
            # always export the labels
            columns += ['taxlot_labels']

        model_views = view_klass.objects.select_related(*select_related).filter(
            **filter_str).order_by('id')

        filename = request.data.get('filename', "ExportedData.csv")
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)

        # get the data in a dict which includes the related data
        data = TaxLotProperty.get_related(model_views, columns)

        # force the data into the same order as the IDs
        if ids:
            order_dict = {obj_id: index for index, obj_id in enumerate(ids)}
            data.sort(key=lambda x: order_dict[x['id']])  # x is the property/taxlot object

        # note that the labels are in the property_labels column and are returned by the
        # TaxLotProperty.get_related method.

        # header
        writer.writerow(columns)

        # iterate over the results to preserve column order and write row.
        # The front end returns columns with prepended tax_ and property_ columns for the
        # related fields. This is an expensive operation and can cause issues with stripping
        # off property_ from items such as propety_name, property_notes, and property_type
        # which are explicitly excluded below
        for datum in data:
            row = []
            for column in columns:
                if column in ['property_name', 'property_notes', 'property_type', 'property_labels']:
                    row.append(datum.get(column, None))
                elif column.startswith('tax_') or column == 'jurisdiction_tax_lot_id':
                    if datum.get('related') and len(datum['related']) > 0:
                        # Looks like related returns a list. Is this as expected?
                        row.append(datum['related'][0].get(re.sub(r'^tax_', '', column), None))
                    else:
                        row.append(None)
                elif column.startswith('property_') or column == 'jurisdiction_tax_lot_id':
                    if datum.get('related') and len(datum['related']) > 0:
                        # Looks like related returns a list. Is this as expected?
                        row.append(datum['related'][0].get(re.sub(r'^property_', '', column), None))
                    else:
                        row.append(None)
                else:
                    row.append(datum.get(column, None))

            writer.writerow(row)

        return response
