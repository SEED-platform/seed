# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class
from seed.models.columns import Column
from seed.serializers.columns import ColumnSerializer
from seed.utils.api import OrgValidateMixin
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet
from seed.utils.api_schema import AutoSchemaHelper

_log = logging.getLogger(__name__)


class ColumnSchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('GET', 'list'): [
                self.org_id_field(),
                self.body_field(
                    name='Column params',
                    required=True,
                    description="An object containing meta data for the GET request: \n"
                                "- Required - Inventory type [property, taxlot] \n"
                                "- Optional - Determine whether or not to show only the used fields "
                                "(i.e. only columns that have been mapped)",
                    params_to_formats={
                        'inventory_type': 'string',
                        'only_used': 'boolean'
                    }
                )
            ],
            ('POST', 'create'): [self.org_id_field()],
            ('GET', 'retrieve'): [self.org_id_field()],
            ('DELETE', 'delete'): [self.org_id_field()]

        }


class ColumnViewSet(OrgValidateMixin, SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    create:
        Create a new Column within user`s specified org.

    update:
        Update a column and modify which dataset it belongs to.

    delete:
        Deletes a single column.
    """

    swagger_schema = ColumnSchema
    raise_exception = True
    serializer_class = ColumnSerializer
    renderer_classes = (JSONRenderer,)
    model = Column
    pagination_class = None
    parser_classes = (JSONParser, FormParser)

    def get_queryset(self):
        # check if the request is properties or taxlots
        org_id = self.get_organization(self.request)
        return Column.objects.filter(organization_id=org_id)

    @ajax_request_class
    def list(self, request):
        """
        Retrieves all columns for the user's organization including the raw database columns. Will
        return all the columns across both the Property and Tax Lot tables. The related field will
        be true if the column came from the other table that is not the 'inventory_type' (which
        defaults to Property)
        ___
        parameters:
           - name: organization_id
             description: The organization_id for this user's organization
             required: true
             paramType: query
           - name: inventory_type
             description: Which inventory type is being matched (for related fields and naming).
               property or taxlot
             required: true
             paramType: query
           - name: used_only
             description: Determine whether or not to show only the used fields (i.e. only columns that have been mapped)
             type: boolean
             required: false
             paramType: query
        type:
           status:
               required: true
               type: string
               description: Either success or error
           columns:
               required: true
               type: array[column]
               description: Returns an array where each item is a full column structure.
        """
        organization_id = self.get_organization(self.request)
        inventory_type = request.query_params.get('inventory_type', 'property')
        only_used = request.query_params.get('only_used', False)
        columns = Column.retrieve_all(organization_id, inventory_type, only_used)
        return JsonResponse({
            'status': 'success',
            'columns': columns,
        })

    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        This API endpoint retrieves a Column
        ---
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
        type:
            status:
                type: string
                description: success or error
                required: true
            column:
                required: true
                type: dictionary
                description: Returns a dictionary of a full column structure with keys such as
                             keys ''name'', ''id'', ''is_extra_data'', ''column_name'',
                             ''table_name'',..
        """
        organization_id = self.get_organization(self.request)

        # check if column exists for the organization
        try:
            c = Column.objects.get(pk=pk)
        except Column.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'column with id {} does not exist'.format(pk)
            }, status=status.HTTP_404_NOT_FOUND)

        if c.organization.id != organization_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Organization ID mismatch between column and organization'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({
            'status': 'success',
            'column': ColumnSerializer(c).data
        })
