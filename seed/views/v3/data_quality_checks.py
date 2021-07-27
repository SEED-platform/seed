# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import csv

from celery.utils.log import get_task_logger
from django.http import JsonResponse, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from unidecode import unidecode

from seed.data_importer.tasks import do_checks
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models.data_quality import DataQualityCheck
from seed.models import PropertyView, TaxLotView
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache_raw

logger = get_task_logger(__name__)


class DataQualityCheckViewSet(viewsets.ViewSet, OrgMixin):
    """
    Handles Data Quality API operations within Inventory backend.
    (1) Post, wait, get…
    (2) Respond with what changed
    """

    # Remove lookup_field once data_quality_check_id is used and "pk" can be used
    lookup_field = 'organization_id'
    # allow organization_id path id to be used for authorization (ie has_perm_class)
    authz_org_id_kwarg = 'organization_id'

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                "organization_id",
                "IN_PATH",
                "Organization ID - identifier used to specify a DataQualityCheck",
                True,
                "TYPE_INTEGER"
            )
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer'],
                'taxlot_view_ids': ['integer'],
            },
            description='An object containing IDs of the records to perform'
                        ' data quality checks on. Should contain two keys- '
                        'property_view_ids and taxlot_view_ids, each of '
                        'which is an array of appropriate IDs.',
        ),
        responses={
            200: AutoSchemaHelper.schema_factory({
                'num_properties': 'integer',
                'num_taxlots': 'integer',
                'progress_key': 'string',
                'progress': {},
            })
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def start(self, request, organization_id):
        """
        This API endpoint will create a new data_quality check process in the background,
        on potentially a subset of properties/taxlots, and return back a query key
        """
        body = request.data
        property_view_ids = body['property_view_ids']
        taxlot_view_ids = body['taxlot_view_ids']

        property_state_ids = PropertyView.objects.filter(
            id__in=property_view_ids,
            property__organization_id=organization_id
        ).values_list('state_id', flat=True)
        taxlot_state_ids = TaxLotView.objects.filter(
            id__in=taxlot_view_ids,
            taxlot__organization_id=organization_id
        ).values_list('state_id', flat=True)

        # For now, organization_id is the only key currently used to identify DataQualityChecks
        return_value = do_checks(organization_id, property_state_ids, taxlot_state_ids)

        return JsonResponse({
            'num_properties': len(property_state_ids),
            'num_taxlots': len(taxlot_state_ids),
            # TODO #239: Deprecate progress_key from here and just use the 'progess.progress_key'
            'progress_key': return_value['progress_key'],
            'progress': return_value,
        })

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("run_id", True, "Import file ID or cache key"),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['GET'])
    def results_csv(self, request):
        """
        Download a CSV of the results from a data quality run based on either the ID that was
        given during the creation of the data quality task or the ID of the
        import file which had it's records checked.
        Note that it is not related to objects in the database, since the results
        are stored in redis!
        """
        run_id = request.query_params.get('run_id')
        if run_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'must include Import file ID or cache key as run_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(run_id, self.get_organization(request)))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Data Quality Check Results.csv"'

        writer = csv.writer(response)
        if data_quality_results is None:
            writer.writerow(['Error'])
            writer.writerow(['data quality results not found'])
            return response

        writer.writerow(
            ['Table', 'Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
             'Applied Label', 'Condition', 'Error Message', 'Severity'])

        for row in data_quality_results:
            for result in row['data_quality_results']:
                writer.writerow([
                    row['data_quality_results'][0]['table_name'],
                    row['address_line_1'],
                    row['pm_property_id'] if 'pm_property_id' in row else None,
                    row['jurisdiction_tax_lot_id'] if 'jurisdiction_tax_lot_id' in row else None,
                    row['custom_id_1'],
                    result['formatted_field'],
                    result.get('label', None),
                    result['condition'],
                    # the detailed_message field can have units which has superscripts/subscripts, so unidecode it!
                    unidecode(result['detailed_message']),
                    result['severity']
                ])

        return response

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("run_id", True, "Import file ID or cache key"),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['GET'])
    def results(self, request):
        """
        Return the results of a data quality run based on either the ID that was
        given during the creation of the data quality task or the ID of the
        import file which had it's records checked.
        Note that it is not related to objects in the database, since the results
        are stored in redis!
        """
        data_quality_id = request.query_params['run_id']
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(data_quality_id, self.get_organization(request)))
        return JsonResponse({
            'data': data_quality_results
        })
