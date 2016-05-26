from django.contrib.auth.decorators import login_required

from seed.bluesky.models import PropertyView, TaxLotView, TaxLotProperty
from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.utils.api import api_endpoint


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_properties(request):
    property_views = PropertyView.objects.select_related('property', 'state', 'cycle') \
        .filter(property__organization_id=request.GET['organization_id'])

    return {
        'property_views': property_views
    }


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_property(request, property_pk):
    property_view = PropertyView.objects.select_related('property', 'cycle', 'state') \
        .filter(property_id=property_pk, property__organization_id=request.GET['organization_id'])

    # Lots this property is on
    lot_view_pks = TaxLotProperty.objects.filter(property_view_id=property_view.pk).values_list('taxlot_view_id', flat=True)
    lot_views = TaxLotView.objects.filter(pk__in=lot_view_pks).select_related('cycle', 'state')
    return {
        'property_view': property_view,
        'lot_views': lot_views,
    }


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlots(request):
    taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
        .filter(property__organization_id=request.GET['organization_id'])

    return {
        'taxlot_views': taxlot_views
    }


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlot(request, taxlot_pk):
    taxlot_view = TaxLotView.objects.select_related('taxlot', 'cycle', 'state') \
        .filter(taxlot_id=taxlot_pk, taxlot__organization_id=request.GET['organization_id'])

    # Properties on this lot
    property_view_pks = TaxLotProperty.objects.filter(taxlot_view_id=taxlot_view.pk).values_list('property_view_id', flat=True)
    property_views = PropertyView.objects.filter(pk__in=property_view_pks).select_related('cycle', 'state')
    return {
        'taxlot_view': taxlot_view,
        'property_views': property_views,
    }

