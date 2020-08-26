# !/usr/bin/env python
# encoding: utf-8

from django.db.models import Subquery
from django.http import JsonResponse

from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.ubid import decode_unique_ids


class UbidViewSet(viewsets.ViewSet, OrgMixin):
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
        ulid_unpopulated = 0
        ulid_successfully_decoded = 0
        ulid_not_decoded = 0
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

            ulid_unpopulated = taxlot_states.filter(ulid__isnull=True).count()
            ulid_successfully_decoded = taxlot_states.filter(
                ulid__isnull=False,
                bounding_box__isnull=False,
                centroid__isnull=False
            ).count()
            # for ulid_not_decoded, bounding_box could be populated from a GeoJSON import
            ulid_not_decoded = taxlot_states.filter(
                ulid__isnull=False,
                centroid__isnull=True
            ).count()

        result = {
            "ubid_unpopulated": ubid_unpopulated,
            "ubid_successfully_decoded": ubid_successfully_decoded,
            "ubid_not_decoded": ubid_not_decoded,
            "ulid_unpopulated": ulid_unpopulated,
            "ulid_successfully_decoded": ulid_successfully_decoded,
            "ulid_not_decoded": ulid_not_decoded,
        }

        return result
