# !/usr/bin/env python
# encoding: utf-8

from django.db.models import Subquery
from django.http import JsonResponse

from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization

from seed.models.properties import PropertyState, PropertyView
from seed.models.tax_lots import TaxLotState, TaxLotView
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.geocode import geocode_buildings


class GeocodeViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer'],
                'taxlot_view_ids': ['integer'],
            },
            description='IDs by inventory type for records to be geocoded.'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def geocode_by_ids(self, request):
        body = dict(request.data)
        property_view_ids = body.get('property_view_ids')
        taxlot_view_ids = body.get('taxlot_view_ids')

        if property_view_ids:
            property_views = PropertyView.objects.filter(id__in=property_view_ids)
            properties = PropertyState.objects.filter(
                id__in=Subquery(property_views.values('state_id'))
            )
            geocode_buildings(properties)

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(id__in=taxlot_view_ids)
            taxlots = TaxLotState.objects.filter(
                id__in=Subquery(taxlot_views.values('state_id'))
            )
            geocode_buildings(taxlots)

        return JsonResponse({'status': 'success'})

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer'],
                'taxlot_view_ids': ['integer'],
            },
            description='IDs by inventory type for records to be used in building a geocoding summary.'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['POST'])
    def confidence_summary(self, request):
        body = dict(request.data)
        property_view_ids = body.get('property_view_ids')
        taxlot_view_ids = body.get('taxlot_view_ids')

        result = {}

        if property_view_ids:
            property_views = PropertyView.objects.filter(id__in=property_view_ids)
            result["properties"] = {
                'not_geocoded': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__isnull=True
                ),
                'high_confidence': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__startswith='High'
                ),
                'low_confidence': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__startswith='Low'
                ),
                'manual': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence='Manually geocoded (N/A)'
                ),
                'missing_address_components': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence='Missing address components (N/A)'
                ),
            }

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(id__in=taxlot_view_ids)
            result["tax_lots"] = {
                'not_geocoded': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__isnull=True
                ),
                'high_confidence': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__startswith='High'
                ),
                'low_confidence': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__startswith='Low'
                ),
                'manual': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence='Manually geocoded (N/A)'
                ),
                'missing_address_components': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence='Missing address components (N/A)'
                ),
            }

        return result
