# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Subquery
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import DATA_STATE_IMPORT, UbidModel
from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.serializers.ubid_models import UbidModelSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)
from seed.utils.ubid import decode_unique_ids, get_jaccard_index, validate_ubid
from seed.utils.viewsets import ModelViewSetWithoutPatch


class UbidViewSet(ModelViewSetWithoutPatch, OrgMixin):
    model = UbidModel
    pagination_class = None
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
                'ubid1': 'string',
                'ubid2': 'string',
            },
            required=['ubid1', 'ubid2'],
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['POST'])
    def get_jaccard_index(self, request):
        """
        Submit a request to compare two UBIDs using the Jaccard Index.
        """
        body = dict(request.data)

        ubid1 = body.get('ubid1')
        ubid2 = body.get('ubid2')

        if ubid1 and ubid2:
            jaccard_index = get_jaccard_index(ubid1, ubid2)
            return JsonResponse({'status': 'success', 'data': jaccard_index})
        else:
            return JsonResponse({
                'status': 'error',
                'errors': 'ubid1 and ubid2 are both required',
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'ubid': 'string',
            },
            required=['ubid'],
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['POST'])
    def validate_ubid(self, request):
        """
        Determines validity of a UBID
        """
        ubid = dict(request.data).get('ubid')

        return JsonResponse({
            'status': 'success',
            'data': {
                'valid': validate_ubid(ubid),
                'ubid': ubid
            }
        })

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        org_id = self.get_organization(request)
        ubid_models = UbidModel.objects.filter(Q(property__organization_id=org_id) | Q(taxlot__organization_id=org_id))

        return JsonResponse({
            'status': 'success',
            'data': self.serializer_class(ubid_models, many=True).data
        })

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        org_id = self.get_organization(request)
        try:
            ubid_model = UbidModel.objects.get(
                Q(pk=pk) & (Q(property__organization_id=org_id) | Q(taxlot__organization_id=org_id))
            )
            return JsonResponse({
                "status": "success",
                "data": self.serializer_class(ubid_model).data
            })
        except UbidModel.DoesNotExist:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': f"UBID with id {pk} does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def create(self, request):
        org_id = self.get_organization(request)
        serializer = UbidModelSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify that the property/taxlot belongs to the org
        if 'property' in request.data:
            try:
                state = PropertyState.objects.get(
                    ~Q(data_state=DATA_STATE_IMPORT),
                    id=request.data.get('property'),
                    organization_id=org_id,
                )
            except PropertyState.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Invalid property id',
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                state = TaxLotState.objects.get(
                    ~Q(data_state=DATA_STATE_IMPORT),
                    id=request.data.get('taxlot'),
                    organization_id=org_id
                )
            except TaxLotState.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'error': 'Invalid taxlot id',
                }, status=status.HTTP_400_BAD_REQUEST)

        # Verify that UBID is not already associated with state
        if state.ubidmodel_set.filter(ubid=request.data.get('ubid')).exists():
            return JsonResponse({
                'status': 'error',
                'error': 'UBID is already associated with id',
            }, status=status.HTTP_400_BAD_REQUEST)

        # If preferred, first set all others to non-preferred without calling save
        if request.data.get('preferred', False):
            state.ubidmodel_set.filter(~Q(ubid=request.data.get('ubid')), preferred=True).update(preferred=False)

        serializer.save()

        return JsonResponse({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'ubid': 'string',
                'preferred': 'boolean',
            },
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk):
        org_id = self.get_organization(request)

        try:
            ubid_model = UbidModel.objects.get(
                Q(pk=pk) & (Q(property__organization_id=org_id) | Q(taxlot__organization_id=org_id))
            )
        except UbidModel.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f"UBID with id {pk} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        valid_fields = ['ubid', 'preferred']
        for field, value in request.data.items():
            if field in valid_fields:
                try:
                    setattr(ubid_model, field, value)
                except ValueError:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid value in request'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid field '{field}' given. Accepted fields are {valid_fields}"
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # If preferred, first set all others to non-preferred without calling save
        state = ubid_model.property or ubid_model.taxlot
        if ubid_model.preferred:
            state.ubidmodel_set.filter(~Q(ubid=request.data.get('ubid')), preferred=True).update(preferred=False)

        ubid_model.save()

        return JsonResponse({
            'status': 'success',
            'data': UbidModelSerializer(ubid_model).data,
        })

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'view_id': 'integer',
                'type': 'string'
            },
            description='Retrieve UBIDs for a Property or TaxLot State associated with a specific view'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['POST'])
    def ubids_by_view(self, request):
        body = dict(request.data)
        org_id = self.get_organization(request)
        view_id = body.get('view_id')
        type = body.get('type')
        accepted_types = ['property', 'taxlot']
        if not view_id or not type or type.lower() not in accepted_types:
            return JsonResponse({
                'status': 'error',
                'message': 'view_id and type (property or taxlot) are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if type.lower() == 'property':
                view = PropertyView.objects.get(
                    id=view_id,
                    cycle__organization_id=org_id
                )
            else:
                view = TaxLotView.objects.get(
                    id=view_id,
                    cycle__organization_id=org_id
                )

            ubids = view.state.ubidmodel_set.all()
            return JsonResponse({
                'status': 'success',
                'data': self.serializer_class(ubids, many=True).data
            })
        except ObjectDoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f"View with id {view_id} does not exist"
            }, status=status.HTTP_404_NOT_FOUND)
