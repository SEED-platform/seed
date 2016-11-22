# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# import datetime
import logging

from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework import viewsets, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import detail_route  # , list_route

from seed.authentication import SEEDAuthentication
from seed.utils.api import api_endpoint_class
from seed.decorators import ajax_request_class  # , require_organization_id_class
# from seed.lib.superperms.orgs.decorators import has_perm_class
from django.contrib.postgres.fields import JSONField
from seed.data_importer.models import ImportFile, ImportRecord, ROW_DELIMITER
from seed.models import (
    obj_to_dict,
    PropertyState,
    TaxLotState,
    DATA_STATE_MAPPING,
)
from seed.utils.mapping import get_mappable_types
from .. import search

_log = logging.getLogger(__name__)


class MappingResultsPayloadSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=100)
    order_by = serializers.CharField(max_length=100)
    filter_params = JSONField()
    page = serializers.IntegerField()
    number_per_page = serializers.IntegerField()


class MappingResultsPropertySerializer(serializers.Serializer):
    pm_property_id = serializers.CharField(max_length=100)
    address_line_1 = serializers.CharField(max_length=100)
    property_name = serializers.CharField(max_length=100)


class MappingResultsTaxLotSerializer(serializers.Serializer):
    pm_property_id = serializers.CharField(max_length=100)
    address_line_1 = serializers.CharField(max_length=100)
    jurisdiction_tax_lot_id = serializers.CharField(max_length=100)


class MappingResultsResponseSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    properties = MappingResultsPropertySerializer(many=True)
    tax_lots = MappingResultsTaxLotSerializer(many=True)
    number_properties_matching_search = serializers.IntegerField()
    number_properties_returned = serializers.IntegerField()
    number_tax_lots_matching_search = serializers.IntegerField()
    number_tax_lots_returned = serializers.IntegerField()


class ImportFileViewSet(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Retrieves details about an ImportFile.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            import_file:
                type: ImportFile structure
                description: full detail of import file
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
        """

        import_file_id = pk
        orgs = request.user.orgs.all()
        try:
            import_file = ImportFile.objects.get(
                pk=import_file_id
            )
            d = ImportRecord.objects.filter(
                super_organization__in=orgs, pk=import_file.import_record_id
            )
        except ObjectDoesNotExist as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not access an import file with this ID'
            }, status=status.HTTP_403_FORBIDDEN)
        # check if user has access to the import file
        if not d.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Could not locate import file with this ID',
                'import_file': {},
            }, status=status.HTTP_400_BAD_REQUEST)

        f = obj_to_dict(import_file)
        f['name'] = import_file.filename_only
        f['dataset'] = obj_to_dict(import_file.import_record)
        # add the importfiles for the matching select
        f['dataset']['importfiles'] = []
        files = f['dataset']['importfiles']
        for i in import_file.import_record.files:
            files.append({
                'name': i.filename_only,
                'id': i.pk
            })
        # make the first element in the list the current import file
        i = files.index({
            'name': import_file.filename_only,
            'id': import_file.pk
        })
        files[0], files[i] = files[i], files[0]

        return JsonResponse({
            'status': 'success',
            'import_file': f,
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def first_five_rows(self, request, pk=None):
        """
        Retrieves the first five rows of an ImportFile.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            first_five_rows:
                type: array of strings
                description: list of strings for each of the first five rows for this import file
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
        """
        import_file = ImportFile.objects.get(pk=pk)
        if import_file is None:
            return JsonResponse({'status': 'error', 'message': 'Could not find import file with pk=' + str(
                pk)}, status=status.HTTP_400_BAD_REQUEST)
        if import_file.cached_second_to_fifth_row is None:
            return JsonResponse({'status': 'error',
                                 'message': 'Internal problem occurred, import file first five rows not cached'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        '''
        import_file.cached_second_to_fifth_row is a field that contains the first
        4 lines of data from the file, split on newlines, delimited by
        ROW_DELIMITER. This becomes an issue when fields have newlines in them,
        so the following is to handle newlines in the fields.
        '''
        lines = []
        for l in import_file.cached_second_to_fifth_row.splitlines():
            if ROW_DELIMITER in l:
                lines.append(l)
            else:
                # Line caused by newline in data, concat it to previous line.
                index = len(lines) - 1
                lines[index] = lines[index] + '\n' + l

        rows = [r.split(ROW_DELIMITER) for r in lines]

        return JsonResponse({
            'status': 'success',
            'first_five_rows': [
                dict(
                    zip(import_file.first_row_columns, row)
                ) for row in rows
            ]
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def raw_column_names(self, request, pk=None):
        """
        Retrieves a list of all column names from an ImportFile.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            raw_columns:
                type: array of strings
                description: list of strings of the header row of the ImportFile
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
        """
        import_file = ImportFile.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'raw_columns': import_file.first_row_columns
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['POST'])
    def filtered_mapping_results(self, request, pk=None):
        """
        Retrieves a paginated list of Properties and Tax Lots for a specific import file after mapping.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import File ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: body
              description: JSON body with filter information; q is search string, order_by is the field to sort by,
                           filter_params is a hash of Django-like filter params
              paramType: body
              pytype: MappingResultsPayloadSerializer
              required: true
        response_serializer: MappingResultsResponseSerializer
        """
        body = request.data
        q = body.get('q', '')
        other_search_params = body.get('filter_params', {})
        order_by = 'id'
        sort_reverse = body.get('sort_reverse', False)
        page = int(body.get('page', 1))
        number_per_page = int(body.get('number_per_page', 10))
        import_file_id = pk
        if sort_reverse:
            order_by = "-%s" % order_by

        properties_initial_qs = PropertyState.objects.order_by(order_by).filter(
            import_file__pk=import_file_id,
            data_state=DATA_STATE_MAPPING,
        )
        taxlots_initial_qs = TaxLotState.objects.order_by(order_by).filter(
            import_file__pk=import_file_id,
            data_state=DATA_STATE_MAPPING,
        )

        fieldnames = [
            # 'pm_property_id',
            'address_line_1',
            'property_name',
        ]
        # add some filters to the dict of known column names so search_buildings
        # doesn't parse them as extra_data
        # TODO: remove the use of get_mappable_types and replace with MappingData.
        db_columns = get_mappable_types()
        db_columns['children__isnull'] = ''
        db_columns['children'] = ''
        db_columns['project__slug'] = ''
        db_columns['import_file_id'] = ''

        # search the query sets
        properties_queryset = search.search_buildings(
            q, fieldnames=fieldnames, queryset=properties_initial_qs
        )
        properties_queryset = search.filter_other_params(
            properties_queryset, other_search_params, db_columns
        )
        properties, properties_count = search.generate_paginated_results(
            properties_queryset, number_per_page=number_per_page, page=page,
            matching=True
        )

        taxlots_queryset = search.search_buildings(
            q, fieldnames=fieldnames, queryset=taxlots_initial_qs
        )
        taxlots_queryset = search.filter_other_params(
            taxlots_queryset, other_search_params, db_columns
        )
        tax_lots, tax_lots_count = search.generate_paginated_results(
            taxlots_queryset, number_per_page=number_per_page, page=page,
            matching=True
        )

        _log.debug("I found {} properties".format(len(properties)))
        _log.debug("I found {} tax lots".format(len(tax_lots)))

        return {
            'status': 'success',
            'properties': properties,
            'tax_lots': tax_lots,
            'number_properties_returned': len(properties),
            'number_properties_matching_search': properties_count,
            'number_tax_lots_returned': len(tax_lots),
            'number_tax_lots_matching_search': tax_lots_count,
        }
