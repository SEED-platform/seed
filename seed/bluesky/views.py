from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict

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

    response = []
    for prop in property_views:
        p = model_to_dict(prop)
        p['state'] = model_to_dict(prop.state)
        p['property'] = model_to_dict(prop.property)
        p['cycle'] = model_to_dict(prop.cycle)
        response.append(p)

    return response


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_property(request, property_pk):
    property_view = PropertyView.objects.select_related('property', 'cycle', 'state') \
        .get(property_id=property_pk, property__organization_id=request.GET['organization_id'])

    # Lots this property is on
    lot_view_pks = TaxLotProperty.objects.filter(property_view_id=property_view.pk).values_list('taxlot_view_id', flat=True)
    lot_views = TaxLotView.objects.filter(pk__in=lot_view_pks).select_related('cycle', 'state')

    p = model_to_dict(property_view)
    p['state'] = model_to_dict(property_view.state)
    p['property'] = model_to_dict(property_view.property)
    p['cycle'] = model_to_dict(property_view.cycle)
    p['lots'] = []

    for lot in lot_views:
        p['lots'].append(model_to_dict(lot))

    return p


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlots(request):
    taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
        .filter(taxlot__organization_id=request.GET['organization_id'])

    response = []
    for lot in taxlot_views:
        l = model_to_dict(lot)
        l['state'] = model_to_dict(lot.state)
        l['taxlot'] = model_to_dict(lot.taxlot)
        l['cycle'] = model_to_dict(lot.cycle)
        response.append(l)

    return response


@require_organization_id
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlot(request, taxlot_pk):
    taxlot_view = TaxLotView.objects.select_related('taxlot', 'cycle', 'state') \
        .get(taxlot_id=taxlot_pk, taxlot__organization_id=request.GET['organization_id'])

    # Properties on this lot
    property_view_pks = TaxLotProperty.objects.filter(taxlot_view_id=taxlot_view.pk).values_list('property_view_id', flat=True)
    property_views = PropertyView.objects.filter(pk__in=property_view_pks).select_related('cycle', 'state')

    l = model_to_dict(taxlot_view)
    l['state'] = model_to_dict(taxlot_view.state)
    l['taxlot'] = model_to_dict(taxlot_view.taxlot)
    l['cycle'] = model_to_dict(taxlot_view.cycle)
    l['properties'] = []

    for prop in property_views:
        l['properties'].append(model_to_dict(prop))

    return l

