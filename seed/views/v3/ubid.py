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
from seed.models import UbidModel
from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.serializers.ubid_models import UbidModelSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)
from seed.utils.ubid import decode_unique_ids, get_jaccard_index


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
    def get_jaccard_index(self, request):
        """
        Submit a request to compare UBIDs using the Jaccard Index for 2 ubids.
        """
        body = dict(request.data)
        self.get_organization(request)

        ubid1 = body.get('ubid1')
        ubid2 = body.get('ubid2')

        if ubid1 and ubid2:
            jaccard_index = get_jaccard_index(ubid1, ubid2)

            return JsonResponse({'status': 'success', 'data': jaccard_index})

        else:
            return JsonResponse({'status': 'failed', 'message': 'exactly 2 ubids are required'})

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

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    def create(self, request):
        serializer = UbidModelSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'failed',
                'errors': 'serializer.errors',
            }, status=status.HTTP_400_BAD_REQUEST)

        ubid_model = serializer.save()
        # if new ubid is preferred, set others to false
        if ubid_model.preferred:
            # find preferred ubids that are not self
            if ubid_model.property:
                ubids = UbidModel.objects.filter(
                    ~Q(id=ubid_model.id),
                    property=ubid_model.property,
                    preferred=True
                )
            else:
                ubids = UbidModel.objects.filter(
                    ~Q(id=ubid_model.id),
                    taxlot=ubid_model.taxlot,
                    preferred=True
                )

            for ubid in ubids:
                ubid.preferred = False
                ubid.save()

        return JsonResponse({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    # overrode endpoint to set to allow partial updates. The default update endpoint requires all fields
    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk):
        org = self.get_organization(request)
        ubid = UbidModel.objects.get(
            Q(pk=pk) & (Q(property__organization=org) | Q(taxlot__organization=org))
        )
        state = ubid.property or ubid.taxlot

        # if the incoming ubid is not preferred and is the current ubid, clear state.ubid
        if request.data.get('ubid') == state.ubid and not request.data.get('preferred'):
            state.ubid = None
            state.save()
        # if the incoming ubid is preferred and different, set state.ubid
        elif request.data.get('ubid') != state.ubid and request.data.get('preferred'):
            state.ubid = ubid.ubid
            state.save()

        valid_fields = [field.name for field in UbidModel._meta.fields]
        for field, value in request.data.items():
            if field in valid_fields:
                setattr(ubid, field, value)
            else:
                return JsonResponse({
                    'status': 'failed',
                    'message': f"Invalid field '{field}' given. Accepted fields are {valid_fields}"
                }, status=status.HTTP_400_BAD_REQUEST)

        ubid.save()
        return JsonResponse({
            'status': 'success',
            'data': UbidModelSerializer(ubid).data,
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'view_id': 'integer',
                'type': 'string'
            },
            description='Retrieve Ubid Models for a given Property View'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def ubids_by_state(self, request):
        body = dict(request.data)
        org_id = self.get_organization(request)
        view_id = body.get('view_id')
        type = body.get('type')
        accepted_types = ['property', 'taxlot']
        if not view_id or not type or type.lower() not in accepted_types:
            return JsonResponse({
                'status': 'failed',
                'message': 'A View ID and type (property or taxlot) are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if type.lower() == 'property':
                view_class = PropertyView
                state_class = PropertyState
            else:
                view_class = TaxLotView
                state_class = TaxLotState

            view = view_class.objects.get(
                id=view_id,
                cycle__organization_id=org_id
            )

            state = state_class.objects.get(
                id=view.state.id
            )
            ubids = state.ubidmodel_set.all()

        except PropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'failed',
                'message': 'No ubids found for given inputs'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            'status': 'success',
            'data': self.serializer_class(ubids, many=True).data
        }, status=status.HTTP_200_OK)
