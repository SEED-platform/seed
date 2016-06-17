from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import model_to_dict

from seed.bluesky.models import Cycle, PropertyView, TaxLotView, TaxLotState, TaxLotProperty
from seed.decorators import ajax_request, require_organization_id, require_organization_membership
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Column
from seed.utils.api import api_endpoint


@require_organization_id
@require_organization_membership
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_properties(request):
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 1)

    cycle_id = request.GET.get('cycle')
    if cycle_id:
        cycle = Cycle.objects.get(organization_id=request.GET['organization_id'], pk=cycle_id)
    else:
        cycle = Cycle.objects.filter(organization_id=request.GET['organization_id']).latest()

    property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
        .filter(property__organization_id=request.GET['organization_id'], cycle=cycle)

    paginator = Paginator(property_views_list, per_page)

    try:
        property_views = paginator.page(page)
        page = int(page)
    except PageNotAnInteger:
        property_views = paginator.page(1)
        page = 1
    except EmptyPage:
        property_views = paginator.page(paginator.num_pages)
        page = paginator.num_pages

    response = {
        'pagination': {
            'page': page,
            'start': paginator.page(page).start_index(),
            'end': paginator.page(page).end_index(),
            'num_pages': paginator.num_pages,
            'has_next': paginator.page(page).has_next(),
            'has_previous': paginator.page(page).has_previous(),
            'total': paginator.count
        },
        'results': []
    }

    # Ids of propertyviews to look up in m2m
    prop_ids = [p.pk for p in property_views]
    joins = TaxLotProperty.objects.filter(property_view_id__in=prop_ids)

    # Get all ids of tax lots on these joins
    taxlot_view_ids = [j.taxlot_view_id for j in joins]

    # Get all tax lot views that are related
    taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle').filter(pk__in=taxlot_view_ids)

    # Map tax lot view id to tax lot view's state data, so we can reference these easily and save some queries.
    taxlot_map = {}
    for taxlot_view in taxlot_views:
        taxlot_state_data = model_to_dict(taxlot_view.state, exclude=['extra_data'])

        # Add extra data fields right to this object.
        for extra_data_field, extra_data_value in taxlot_view.state.extra_data.items():
            taxlot_state_data[extra_data_field] = extra_data_value
        taxlot_map[taxlot_view.pk] = taxlot_state_data

    # A mapping of property view pk to a list of taxlot state info for a taxlot view
    join_map = {}
    for join in joins:
        join_dict = taxlot_map[join.taxlot_view_id].copy()
        join_dict.update({
            'primary': 'P' if join.primary else 'S'
        })
        try:
            join_map[join.property_view_id].append(join_dict)
        except KeyError:
            join_map[join.property_view_id] = [join_dict]

    for prop in property_views:
        # Each object in the response is built from the state data, with related data added on.
        p = model_to_dict(prop.state, exclude=['extra_data'])

        for extra_data_field, extra_data_value in prop.state.extra_data.items():
            p[extra_data_field] = extra_data_value

        p['campus'] = prop.property.campus

        # All the related tax lot states.
        p['related'] = join_map.get(prop.pk, [])

        # Start collapsed field data
        # Map of fields in related model to unique list of values
        related_field_map = {}

        # Iterate over related dicts and gather field values.
        # Basically get a unique list off all related values for each field.
        for related in p['related']:
            for k, v in related.items():
                try:
                    related_field_map[k].add(v)
                except KeyError:
                    try:
                        related_field_map[k] = set([v])
                    except TypeError:
                        # Extra data field, ignore it
                        pass

        for k, v in related_field_map.items():
            related_field_map[k] = list(v)

        p['collapsed'] = related_field_map
        # End collapsed field data

        response['results'].append(p)

    return response


@require_organization_id
@require_organization_membership
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
@require_organization_membership
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlots(request):
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 1)

    cycle_id = request.GET.get('cycle')
    if cycle_id:
        cycle = Cycle.objects.get(organization_id=request.GET['organization_id'], pk=cycle_id)
    else:
        cycle = Cycle.objects.filter(organization_id=request.GET['organization_id']).latest()

    taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
        .filter(taxlot__organization_id=request.GET['organization_id'], cycle=cycle)

    paginator = Paginator(taxlot_views_list, per_page)

    try:
        taxlot_views = paginator.page(page)
        page = int(page)
    except PageNotAnInteger:
        taxlot_views = paginator.page(1)
        page = 1
    except EmptyPage:
        taxlot_views = paginator.page(paginator.num_pages)
        page = paginator.num_pages

    response = {
        'pagination': {
            'page': page,
            'start': paginator.page(page).start_index(),
            'end': paginator.page(page).end_index(),
            'num_pages': paginator.num_pages,
            'has_next': paginator.page(page).has_next(),
            'has_previous': paginator.page(page).has_previous(),
            'total': paginator.count
        },
        'results': []
    }

    # Ids of taxlotviews to look up in m2m
    lot_ids = [l.pk for l in taxlot_views]
    joins = TaxLotProperty.objects.filter(taxlot_view_id__in=lot_ids)

    # Get all ids of properties on these joins
    property_view_ids = [j.property_view_id for j in joins]

    # Get all property views that are related
    property_views = PropertyView.objects.select_related('property', 'state', 'cycle').filter(pk__in=property_view_ids)

    # Map property view id to property view's state data, so we can reference these easily and save some queries.
    property_map = {}
    for property_view in property_views:
        property_data = model_to_dict(property_view.state, exclude=['extra_data'])
        property_data['campus'] = property_view.property.campus

        # Add extra data fields right to this object.
        for extra_data_field, extra_data_value in property_view.state.extra_data.items():
            property_data[extra_data_field] = extra_data_value
        property_map[property_view.pk] = property_data

    # A mapping of taxlot view pk to a list of property state info for a property view
    join_map = {}
    for join in joins:

        # Find all the taxlot ids that this property relates to
        related_taxlot_view_ids = TaxLotProperty.objects.filter(property_view_id=join.property_view_id) \
            .values_list('taxlot_view_id', flat=True)
        state_ids = TaxLotView.objects.filter(pk__in=related_taxlot_view_ids)
        jurisdiction_taxlot_identifiers = TaxLotState.objects.filter(pk__in=state_ids) \
            .values_list('jurisdiction_taxlot_identifier', flat=True)

        join_dict = property_map[join.property_view_id].copy()
        join_dict.update({
            'primary': 'P' if join.primary else 'S',
            'calculated_taxlot_ids': ', '.join(jurisdiction_taxlot_identifiers)
        })
        try:
            join_map[join.taxlot_view_id].append(join_dict)
        except KeyError:
            join_map[join.taxlot_view_id] = [join_dict]

    for lot in taxlot_views:
        # Each object in the response is built from the state data, with related data added on.
        l = model_to_dict(lot.state, exclude=['extra_data'])

        for extra_data_field, extra_data_value in lot.state.extra_data.items():
            l[extra_data_field] = extra_data_value

        l['related'] = join_map.get(lot.pk, [])

        # Start collapsed field data
        # Map of fields in related model to unique list of values
        related_field_map = {}

        # Iterate over related dicts and gather field values
        for related in l['related']:
            for k, v in related.items():
                try:
                    related_field_map[k].add(v)
                except KeyError:
                    try:
                        related_field_map[k] = set([v])
                    except TypeError:
                        # Extra data field, ignore it
                        pass

        for k, v in related_field_map.items():
            related_field_map[k] = list(v)

        l['collapsed'] = related_field_map
        # End collapsed field data

        response['results'].append(l)

    return response


@require_organization_id
@require_organization_membership
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


@require_organization_id
@require_organization_membership
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_cycles(request):
    cycles = Cycle.objects.filter(organization_id=request.GET['organization_id'])
    response = []
    for cycle in cycles:
        response.append({
            'pk': cycle.pk,
            'name': cycle.name
        })
    return response


@require_organization_id
@require_organization_membership
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_property_columns(request):
    columns = [
        {'field': 'building_portfolio_manager_identifier', 'display': 'PM Property ID', 'related': False, 'extra_data': False},
        {'field': 'jurisdiction_property_identifier', 'display': 'Property / Building ID', 'related': False},
        {'field': 'jurisdiction_taxlot_identifier', 'display': 'Tax Lot ID', 'related': True},
        {'field': 'primary', 'display': 'Primary/Secondary', 'related': True},
        {'field': 'no_field', 'display': 'Associated TaxLot IDs', 'related': False},
        {'field': 'no_field', 'display': 'Associated Building Tax Lot ID', 'related': False},
        {'field': 'address', 'display': 'Tax Lot Address', 'related': True},
        {'field': 'address_line_1', 'display': 'Property Address 1', 'related': False},
        {'field': 'city', 'display': 'Property City', 'related': False},
        {'field': 'property_name', 'display': 'Property Name', 'related': False},
        {'field': 'campus', 'display': 'Campus', 'related': False},
        {'field': 'no_field', 'display': 'PM Parent Property ID', 'related': False},
        {'field': 'gross_floor_area', 'display': 'Property Floor Area', 'related': False},
        {'field': 'use_description', 'display': 'Property Type', 'related': False},
        {'field': 'energy_score', 'display': 'ENERGY STAR Score', 'related': False},
        {'field': 'site_eui', 'display': 'Site EUI (kBtu/sf-yr)', 'related': False},
        {'field': 'property_notes', 'display': 'Property Notes', 'related': False},
        {'field': 'year_ending', 'display': 'Benchmarking year', 'related': False},
        {'field': 'owner', 'display': 'Owner', 'related': False},
        {'field': 'owner_email', 'display': 'Owner Email', 'related': False},
        {'field': 'owner_telephone', 'display': 'Owner Telephone', 'related': False},
        {'field': 'generation_date', 'display': 'PM Generation Date', 'related': False},
        {'field': 'release_date', 'display': 'PM Release Date', 'related': False},
        {'field': 'address_line_2', 'display': 'Property Address 2', 'related': False},
        {'field': 'state', 'display': 'Property State', 'related': False},
        {'field': 'postal_code', 'display': 'Property Postal Code', 'related': False},
        {'field': 'building_count', 'display': 'Number of Buildings', 'related': False},
        {'field': 'year_built', 'display': 'Year Built', 'related': False},
        {'field': 'recent_sale_date', 'display': 'Property Sale Data', 'related': False},
        {'field': 'conditioned_floor_area', 'display': 'Property Conditioned Floor Area', 'related': False},
        {'field': 'occupied_floor_area', 'display': 'Property Occupied Floor Area', 'related': False},
        {'field': 'owner_address', 'display': 'Owner Address', 'related': False},
        {'field': 'owner_city_state', 'display': 'Owner City/State', 'related': False},
        {'field': 'owner_postal_code', 'display': 'Owner Postal Code', 'related': False},
        {'field': 'building_home_energy_score_identifier', 'display': 'Home Energy Saver ID', 'related': False},
        {'field': 'source_eui_weather_normalized', 'display': 'Source EUI Weather Normalized', 'related': False},
        {'field': 'site_eui_weather_normalized', 'display': 'Site EUI Normalized', 'related': False},
        {'field': 'source_eui', 'display': 'Source EUI', 'related': False},
        {'field': 'energy_alerts', 'display': 'Energy Alerts', 'related': False},
        {'field': 'space_alerts', 'display': 'Space Alerts', 'related': False},
        {'field': 'building_certification', 'display': 'Building Certification', 'related': False},
        {'field': 'city', 'display': 'Tax Lot City', 'related': True},
        {'field': 'state', 'display': 'Tax Lot State', 'related': True},
        {'field': 'postal_code', 'display': 'Tax Lot Postal Code', 'related': True},
        {'field': 'number_properties', 'display': 'Number Properties', 'related': True},
        {'field': 'block_number', 'display': 'Block Number', 'related': True},
        {'field': 'district', 'display': 'District', 'related': True}
    ]

    extra_data_columns = Column.objects.filter(
        organization_id=request.GET['organization_id'],
        is_extra_data=True,
        extra_data_source__isnull=False
    )

    for c in extra_data_columns:
        columns.append({
            'field': c.column_name,
            'display': '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source]),
            'related': c.extra_data_source == Column.SOURCE_TAXLOT,
            'source': Column.SOURCE_CHOICES_MAP[c.extra_data_source],
        })
    return columns


@require_organization_id
@require_organization_membership
@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_taxlot_columns(request):
    columns = [
        {'field': 'jurisdiction_taxlot_identifier', 'display': 'Tax Lot ID', 'related': False},
        {'field': 'calculated_taxlot_ids', 'display': 'Associated TaxLot IDs', 'related': True},
        {'field': 'no_field', 'display': 'Associated Building Tax Lot ID', 'related': False},
        {'field': 'address', 'display': 'Tax Lot Address', 'related': False},
        {'field': 'city', 'display': 'Tax Lot City', 'related': False},
        {'field': 'state', 'display': 'Tax Lot State', 'related': False},
        {'field': 'postal_code', 'display': 'Tax Lot Postal Code', 'related': False},
        {'field': 'number_properties', 'display': 'Number Properties', 'related': False},
        {'field': 'block_number', 'display': 'Block Number', 'related': False},
        {'field': 'district', 'display': 'District', 'related': False},
        {'field': 'primary', 'display': 'Primary/Secondary', 'related': True},
        {'field': 'property_name', 'display': 'Property Name', 'related': True},
        {'field': 'campus', 'display': 'Campus', 'related': True},
        {'field': 'no_field', 'display': 'PM Parent Property ID', 'related': False},
        {'field': 'jurisdiction_property_identifier', 'display': 'Property / Building ID', 'related': True},
        {'field': 'building_portfolio_manager_identifier', 'display': 'PM Property ID', 'related': True},
        {'field': 'gross_floor_area', 'display': 'Property Floor Area', 'related': True},
        {'field': 'use_description', 'display': 'Property Type', 'related': True},
        {'field': 'energy_score', 'display': 'ENERGY STAR Score', 'related': True},
        {'field': 'site_eui', 'display': 'Site EUI (kBtu/sf-yr)', 'related': True},
        {'field': 'property_notes', 'display': 'Property Notes', 'related': True},
        {'field': 'year_ending', 'display': 'Benchmarking year', 'related': True},
        {'field': 'owner', 'display': 'Owner', 'related': True},
        {'field': 'owner_email', 'display': 'Owner Email', 'related': True},
        {'field': 'owner_telephone', 'display': 'Owner Telephone', 'related': True},
        {'field': 'generation_date', 'display': 'PM Generation Date', 'related': True},
        {'field': 'release_date', 'display': 'PM Release Date', 'related': True},
        {'field': 'address_line_1', 'display': 'Property Address 1', 'related': True},
        {'field': 'address_line_2', 'display': 'Property Address 2', 'related': True},
        {'field': 'city', 'display': 'Property City', 'related': True},
        {'field': 'state', 'display': 'Property State', 'related': True},
        {'field': 'postal_code', 'display': 'Property Postal Code', 'related': True},
        {'field': 'building_count', 'display': 'Number of Buildings', 'related': True},
        {'field': 'year_built', 'display': 'Year Built', 'related': True},
        {'field': 'recent_sale_date', 'display': 'Property Sale Data', 'related': True},
        {'field': 'conditioned_floor_area', 'display': 'Property Conditioned Floor Area', 'related': True},
        {'field': 'occupied_floor_area', 'display': 'Property Occupied Floor Area', 'related': True},
        {'field': 'owner_address', 'display': 'Owner Address', 'related': True},
        {'field': 'owner_city_state', 'display': 'Owner City/State', 'related': True},
        {'field': 'owner_postal_code', 'display': 'Owner Postal Code', 'related': True},
        {'field': 'building_home_energy_score_identifier', 'display': 'Home Energy Saver ID', 'related': True},
        {'field': 'source_eui_weather_normalized', 'display': 'Source EUI Weather Normalized', 'related': True},
        {'field': 'site_eui_weather_normalized', 'display': 'Site EUI Normalized', 'related': True},
        {'field': 'source_eui', 'display': 'Source EUI', 'related': True},
        {'field': 'energy_alerts', 'display': 'Energy Alerts', 'related': True},
        {'field': 'space_alerts', 'display': 'Space Alerts', 'related': True},
        {'field': 'building_certification', 'display': 'Building Certification', 'related': True},
        {'field': 'lot_number', 'display': 'Associated Tax Lot ID', 'related': True}
    ]

    extra_data_columns = Column.objects.filter(
        organization_id=request.GET['organization_id'],
        is_extra_data=True,
        extra_data_source__isnull=False
    )

    for c in extra_data_columns:
        columns.append({
            'field': c.column_name,
            'display': '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source]),
            'related': c.extra_data_source == Column.SOURCE_PROPERTY,
            'source': Column.SOURCE_CHOICES_MAP[c.extra_data_source],
        })
    return columns
