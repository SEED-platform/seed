# !/usr/bin/env python
# encoding: utf-8

from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization

from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState

from seed.utils.api import api_endpoint_class
from seed.utils.geocode import geocode_buildings


class GeocodeViews(viewsets.ViewSet):

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def geocode_by_ids(self, request):
        body = dict(request.data)
        property_ids = body.get('property_ids')
        taxlot_ids = body.get('taxlot_ids')

        if property_ids:
            properties = PropertyState.objects.filter(id__in=property_ids)
            geocode_buildings(properties)

        if taxlot_ids:
            taxlots = TaxLotState.objects.filter(id__in=taxlot_ids)
            geocode_buildings(taxlots)

    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def confidence_summary(self, request):
        body = dict(request.data)
        property_ids = body.get('property_ids')
        tax_lot_ids = body.get('tax_lot_ids')

        result = {}

        if property_ids:
            result["properties"] = {
                'not_geocoded': len(PropertyState.objects.filter(
                    id__in=property_ids,
                    geocoding_confidence__isnull=True
                )),
                'high_confidence': len(PropertyState.objects.filter(
                    id__in=property_ids,
                    geocoding_confidence__startswith='High'
                )),
                'low_confidence': len(PropertyState.objects.filter(
                    id__in=property_ids,
                    geocoding_confidence__startswith='Low'
                )),
                'manual': len(PropertyState.objects.filter(
                    id__in=property_ids,
                    geocoding_confidence='Manually geocoded (N/A)'
                )),
                'missing_address_components': len(PropertyState.objects.filter(
                    id__in=property_ids,
                    geocoding_confidence='Missing address components (N/A)'
                )),
            }

        if tax_lot_ids:
            result["tax_lots"] = {
                'not_geocoded': len(TaxLotState.objects.filter(
                    id__in=tax_lot_ids,
                    geocoding_confidence__isnull=True
                )),
                'high_confidence': len(TaxLotState.objects.filter(
                    id__in=tax_lot_ids,
                    geocoding_confidence__startswith='High'
                )),
                'low_confidence': len(TaxLotState.objects.filter(
                    id__in=tax_lot_ids,
                    geocoding_confidence__startswith='Low'
                )),
                'manual': len(TaxLotState.objects.filter(
                    id__in=tax_lot_ids,
                    geocoding_confidence='Manually geocoded (N/A)'
                )),
                'missing_address_components': len(TaxLotState.objects.filter(
                    id__in=tax_lot_ids,
                    geocoding_confidence='Missing address components (N/A)'
                )),
            }

        return result

    @ajax_request_class
    @action(detail=False, methods=['GET'])
    def api_key_exists(self, request):
        org_id = request.GET.get("organization_id")
        org = Organization.objects.get(id=org_id)

        if org.mapquest_api_key:
            return True
        else:
            return False
