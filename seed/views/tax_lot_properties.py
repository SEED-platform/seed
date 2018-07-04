# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import csv
import datetime
from collections import OrderedDict

from django.http import JsonResponse, HttpResponse
from quantityfield import ureg
from rest_framework.decorators import list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    PropertyView,
    TaxLotProperty,
    TaxLotView,
    ColumnListSetting,
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
        Download a csv of the TaxLot and Properties

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
            - name: profile_id
              description: Either an id of a list settings profile, or undefined
              paramType: body
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        org_id = request.query_params['organization_id']
        if 'profile_id' not in request.data:
            profile_id = None
        else:
            if request.data['profile_id'] == 'None':
                profile_id = None
            else:
                profile_id = request.data['profile_id']

        # get the class to operate on and the relationships
        view_klass_str = request.query_params.get('inventory_type', 'properties')
        view_klass = INVENTORY_MODELS[view_klass_str]

        # Set the first column to be the ID
        column_name_mappings = OrderedDict([('id', 'ID')])
        column_ids, add_column_name_mappings, columns_from_database = ColumnListSetting.return_columns(org_id,
                                                                                                       profile_id,
                                                                                                       view_klass_str)
        column_name_mappings.update(add_column_name_mappings)
        select_related = ['state', 'cycle']
        ids = request.data.get('ids', [])
        filter_str = {'cycle': cycle_pk}
        if hasattr(view_klass, 'property'):
            select_related.append('property')
            filter_str = {'property__organization_id': org_id}
            if ids:
                filter_str['property__id__in'] = ids
            # always export the labels
            column_name_mappings['property_labels'] = 'Property Labels'

        elif hasattr(view_klass, 'taxlot'):
            select_related.append('taxlot')
            filter_str = {'taxlot__organization_id': org_id}
            if ids:
                filter_str['taxlot__id__in'] = ids
            # always export the labels
            column_name_mappings['taxlot_labels'] = 'Tax Lot Labels'

        model_views = view_klass.objects.select_related(*select_related).filter(**filter_str).order_by('id')

        filename = request.data.get('filename', "ExportedData.csv")
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)

        # get the data in a dict which includes the related data
        data = TaxLotProperty.get_related(model_views, column_ids, columns_from_database)

        # force the data into the same order as the IDs
        if ids:
            order_dict = {obj_id: index for index, obj_id in enumerate(ids)}
            data.sort(key=lambda x: order_dict[x['id']])  # x is the property/taxlot object

        # header
        writer.writerow(column_name_mappings.values())

        # iterate over the results to preserve column order and write row.
        for datum in data:
            row = []
            for column in column_name_mappings.keys():
                row_result = datum.get(column, None)

                # Try grabbing the value out of the related field if not found yet.
                if row_result is None and datum.get('related'):
                    row_result = datum['related'][0].get(column, None)

                # Convert quantities (this is typically handled in the JSON Encoder, but that isn't here).
                if isinstance(row_result, ureg.Quantity):
                    row_result = row_result.magnitude
                elif isinstance(row_result, datetime.datetime):
                    row_result = row_result.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(row_result, datetime.date):
                    row_result = row_result.strftime("%Y-%m-%d")
                row.append(row_result)

            writer.writerow(row)

        return response
