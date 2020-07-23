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
from seed.utils.geocode import geocode_buildings


class GeocodeViewSet(viewsets.ViewSet, OrgMixin):

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
        """
        Submit a request to geocode property and tax lot records.
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
            geocode_buildings(properties)

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(
                id__in=taxlot_view_ids,
                cycle__organization_id=org_id
            )
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
        """
        Generate a summary of geocoding confidence values for property and
        tax lot records.
        """
        body = dict(request.data)
        org_id = self.get_organization(request)
        property_view_ids = body.get('property_view_ids')
        taxlot_view_ids = body.get('taxlot_view_ids')

        result = {}

        if property_view_ids:
            property_views = PropertyView.objects.filter(
                id__in=property_view_ids,
                cycle__organization_id=org_id
            )
            result["properties"] = {
                'not_geocoded': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__isnull=True
                ).count(),
                'high_confidence': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__startswith='High'
                ).count(),
                'low_confidence': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence__startswith='Low'
                ).count(),
                'manual': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence='Manually geocoded (N/A)'
                ).count(),
                'missing_address_components': PropertyState.objects.filter(
                    id__in=Subquery(property_views.values('state_id')),
                    geocoding_confidence='Missing address components (N/A)'
                ).count(),
            }

        if taxlot_view_ids:
            taxlot_views = TaxLotView.objects.filter(
                id__in=taxlot_view_ids,
                cycle__organization_id=org_id
            )
            result["tax_lots"] = {
                'not_geocoded': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__isnull=True
                ).count(),
                'high_confidence': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__startswith='High'
                ).count(),
                'low_confidence': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence__startswith='Low'
                ).count(),
                'manual': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence='Manually geocoded (N/A)'
                ).count(),
                'missing_address_components': TaxLotState.objects.filter(
                    id__in=Subquery(taxlot_views.values('state_id')),
                    geocoding_confidence='Missing address components (N/A)'
                ).count(),
            }

        return result
