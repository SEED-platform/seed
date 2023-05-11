# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db.models import Q, Subquery
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.models import UbidModel
from seed.serializers.ubid_models import UbidModelSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)
from seed.utils.ubid import decode_unique_ids


class UbidViewSet(viewsets.ModelViewSet, OrgMixin):
    model = UbidModel
    serializer_class = UbidModelSerializer
    queryset = UbidModel.objects.all()
    
    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer'],
                'taxlot_view_ids': ['integer'],
            },
            description='IDs by inventory type for records to have their UBID decoded.'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def decode_by_ids(self, request):
        """
        Submit a request to decode UBIDs for property and tax lot records.
        """
        body = dict(request.data)
        org_id = self.get_organization(request)
        property_view_ids = body.get('property_view_ids')
        taxlot_view_ids = body.get('taxlot_view_ids')

        if property_view_ids:
            property_views = PropertyView.objects.filter(
                id__in=property_view_ids,
                cycle__organization_id=org_id
            )
            properties = PropertyState.objects.filter(
                id__in=Subquery(property_views.values('state_id'))
            )
            decode_unique_ids(properties)

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(
                id__in=taxlot_view_ids,
                cycle__organization_id=org_id
            )
            taxlots = TaxLotState.objects.filter(
                id__in=Subquery(taxlot_views.values('state_id'))
            )
            decode_unique_ids(taxlots)

        return JsonResponse({'status': 'success'})

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer'],
                'taxlot_view_ids': ['integer'],
            },
            description='IDs by inventory type for records to be used in building a UBID decoding summary.'
        )
    )
    @ajax_request_class
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['POST'])
    def decode_results(self, request):
        """
        Generate a summary of populated, unpopulated, and decoded UBIDs for
        property and tax lot records.
        """
        body = dict(request.data)
        org_id = self.get_organization(request)

        ubid_unpopulated = 0
        ubid_successfully_decoded = 0
        ubid_not_decoded = 0
        property_view_ids = body.get('property_view_ids')
        taxlot_view_ids = body.get('taxlot_view_ids')
        if property_view_ids:
            property_views = PropertyView.objects.filter(
                id__in=property_view_ids,
                cycle__organization_id=org_id
            )
            property_states = PropertyState.objects.filter(id__in=Subquery(property_views.values('state_id')))

            ubid_unpopulated = property_states.filter(ubid__isnull=True).count()
            ubid_successfully_decoded = property_states.filter(
                ubid__isnull=False,
                bounding_box__isnull=False,
                centroid__isnull=False
            ).count()
            # for ubid_not_decoded, bounding_box could be populated from a GeoJSON import
            ubid_not_decoded = property_states.filter(
                ubid__isnull=False,
                centroid__isnull=True
            ).count()

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(
                id__in=taxlot_view_ids,
                cycle__organization_id=org_id
            )
            taxlot_states = TaxLotState.objects.filter(id__in=Subquery(taxlot_views.values('state_id')))

            ubid_unpopulated = taxlot_states.filter(ubid__isnull=True).count()
            ubid_successfully_decoded = taxlot_states.filter(
                ubid__isnull=False,
                bounding_box__isnull=False,
                centroid__isnull=False
            ).count()
            # for ubid_not_decoded, bounding_box could be populated from a GeoJSON import
            ubid_not_decoded = taxlot_states.filter(
                ubid__isnull=False,
                centroid__isnull=True
            ).count()

        result = {
            "ubid_unpopulated": ubid_unpopulated,
            "ubid_successfully_decoded": ubid_successfully_decoded,
            "ubid_not_decoded": ubid_not_decoded,

        }

        return result

    # override endpoint to set response to json, not OrderedDict
    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        org = self.get_organization(request)
        ubids = UbidModel.objects.filter(Q(property__organization=org) | Q(taxlot__organization=org))

        return JsonResponse(
            {
                "status": "success",
                "data": self.serializer_class(ubids, many=True).data
            },
            status=status.HTTP_200_OK
        )

    # overrode endpoint to set response to json, not OrderedDict
    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk):
        org = self.get_organization(request)
        try:
            ubid = UbidModel.objects.get(
                Q(pk=pk) & (Q(property__organization=org) | Q(taxlot__organization=org))
            )
            return JsonResponse(
                {
                    "status": "success",
                    "data": self.serializer_class(ubid).data
                },
                status=status.HTTP_200_OK
            )
        except UbidModel.DoesNotExist:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': f'Ubid with id {pk} does not exist'
                },
                status=status.HTTP_404_NOT_FOUND
            )

    # overrode endpoint to set to allow partial updates. The default update endpoint requires all fields
    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk):
        org = self.get_organization(request)
        ubid = UbidModel.objects.get(
            Q(pk=pk) & (Q(property__organization=org) | Q(taxlot__organization=org))
        )
        valid_fields = [field.name for field in UbidModel._meta.fields]

        for field, value in request.data.items():
            if field in valid_fields:
                setattr(ubid, field, value)
            else:
                return JsonResponse({
                    'success': False,
                    'message': f"Invalid field '{field}' given. Accepted fields are {valid_fields}"
                }, status=status.HTTP_400_BAD_REQUEST)

        ubid.save()
        return JsonResponse({
            'status': 'success',
            'data': UbidModelSerializer(ubid).data,
        }, status=status.HTTP_200_OK)
