# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import model_to_dict

from seed.models import Cycle, PropertyView, TaxLotView, TaxLotState, TaxLotProperty
from seed.decorators import ajax_request, require_organization_id, require_organization_membership
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Column
from seed.utils.api import api_endpoint
import itertools

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


def unique(lol):
    """Calculate unique elements in a list of lists."""
    return sorted(set(itertools.chain.from_iterable(lol)))


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
                        related_field_map[k] = {v}
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
    lot_view_pks = TaxLotProperty.objects.filter(property_view_id=property_view.pk).values_list('taxlot_view_id',
                                                                                                flat=True)
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

    # FIXME
    # Temporarily disable paging on this view - does not seem to work.
    # per_page = request.GET.get('per_page', 1)
    per_page = 15000

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
        state_ids = TaxLotView.objects.filter(pk__in=related_taxlot_view_ids).values_list('state_id', flat=True)

        jurisdiction_taxlot_identifiers = TaxLotState.objects.filter(pk__in=state_ids) \
            .values_list('jurisdiction_taxlot_identifier', flat=True)

        # Filter out associated tax lots that are present but which do not have preferred
        none_in_juridiction_tax_lot_ids = None in jurisdiction_taxlot_identifiers
        jurisdiction_taxlot_identifiers = filter(lambda x: x is not None, jurisdiction_taxlot_identifiers)

        if none_in_juridiction_tax_lot_ids:
            jurisdiction_taxlot_identifiers.append("Missing")

        # jurisdiction_taxlot_identifiers = [""]

        join_dict = property_map[join.property_view_id].copy()
        join_dict.update({
            'primary': 'P' if join.primary else 'S',
            'calculated_taxlot_ids': '; '.join(jurisdiction_taxlot_identifiers)
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
                        related_field_map[k] = {v}
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
    property_view_pks = TaxLotProperty.objects.filter(taxlot_view_id=taxlot_view.pk).values_list('property_view_id',
                                                                                                 flat=True)
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
        {
            'name': 'building_portfolio_manager_identifier',
            'displayName': 'PM Property ID',
            'pinnedLeft': True,
            'type': 'number',
            'related': False
        }, {
            'name': 'jurisdiction_property_identifier',
            'displayName': 'Property / Building ID',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'jurisdiction_taxlot_identifier',
            'displayName': 'Tax Lot ID',
            'type': 'numberStr',
            'related': True
        }, {
            'name': 'primary',
            'displayName': 'Primary/Secondary',
            'related': True
        }, {
            # INCOMPLETE, FIELD DOESN'T EXIST
            'name': 'associated_tax_lot_ids',
            'displayName': 'Associated TaxLot IDs',
            'type': 'number',
            'related': False
        }, {
            'name': 'lot_number',
            'displayName': 'Associated Building Tax Lot ID',
            'type': 'number',
            'related': False
        }, {
            'name': 'address',
            'displayName': 'Tax Lot Address',
            'type': 'numberStr',
            'related': True
        }, {
            'name': 'address_line_1',
            'displayName': 'Property Address 1',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'city',
            'displayName': 'Property City',
            'related': False
        }, {
            'name': 'property_name',
            'displayName': 'Property Name',
            'related': False
        }, {
            'name': 'campus',
            'displayName': 'Campus',
            'type': 'boolean',
            'related': False
        }, {
            # INCOMPLETE, FIELD DOESN'T EXIST
            'name': 'pm_parent_property_id',
            'displayName': 'PM Parent Property ID',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'gross_floor_area',
            'displayName': 'Property Floor Area',
            'type': 'number',
            'related': False
        }, {
            'name': 'use_description',
            'displayName': 'Property Type',
            'related': False
        }, {
            'name': 'energy_score',
            'displayName': 'ENERGY STAR Score',
            'type': 'number',
            'related': False
        }, {
            'name': 'site_eui',
            'displayName': 'Site EUI (kBtu/sf-yr)',
            'type': 'number',
            'related': False
        }, {
            'name': 'property_notes',
            'displayName': 'Property Notes',
            'related': False
        }, {
            'name': 'year_ending',
            'displayName': 'Benchmarking year',
            'related': False
        }, {
            'name': 'owner',
            'displayName': 'Owner',
            'related': False
        }, {
            'name': 'owner_email',
            'displayName': 'Owner Email',
            'related': False
        }, {
            'name': 'owner_telephone',
            'displayName': 'Owner Telephone',
            'related': False
        }, {
            'name': 'address_line_2',
            'displayName': 'Property Address 2',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'state',
            'displayName': 'Property State',
            'related': False
        }, {
            'name': 'postal_code',
            'displayName': 'Property Postal Code',
            'type': 'number',
            'related': False
        }, {
            'name': 'building_count',
            'displayName': 'Number of Buildings',
            'type': 'number',
            'related': False
        }, {
            'name': 'year_built',
            'displayName': 'Year Built',
            'related': False
        }, {
            'name': 'recent_sale_date',
            'displayName': 'Property Sale Date',
            'related': False
        }, {
            'name': 'conditioned_floor_area',
            'displayName': 'Property Conditioned Floor Area',
            'type': 'number',
            'related': False
        }, {
            'name': 'occupied_floor_area',
            'displayName': 'Property Occupied Floor Area',
            'type': 'number',
            'related': False
        }, {
            'name': 'owner_address',
            'displayName': 'Owner Address',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'owner_city_state',
            'displayName': 'Owner City/State',
            'related': False
        }, {
            'name': 'owner_postal_code',
            'displayName': 'Owner Postal Code',
            'type': 'number',
            'related': False
        }, {
            'name': 'building_home_energy_score_identifier',
            'displayName': 'Home Energy Score ID',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'generation_date',
            'displayName': 'PM Generation Date',
            'related': False
        }, {
            'name': 'release_date',
            'displayName': 'PM Release Date',
            'related': False
        }, {
            'name': 'source_eui_weather_normalized',
            'displayName': 'Source EUI Weather Normalized',
            'type': 'number',
            'related': False
        }, {
            'name': 'site_eui_weather_normalized',
            'displayName': 'Site EUI Weather Normalized',
            'type': 'number',
            'related': False
        }, {
            'name': 'source_eui',
            'displayName': 'Source EUI',
            'type': 'number',
            'related': False
        }, {
            'name': 'energy_alerts',
            'displayName': 'Energy Alerts',
            'related': False
        }, {
            'name': 'space_alerts',
            'displayName': 'Space Alerts',
            'related': False
        }, {
            'name': 'building_certification',
            'displayName': 'Building Certification',
            'related': False
        }, {
            # Modified field name
            'name': 'tax_city',
            'displayName': 'Tax Lot City',
            'related': True
        }, {
            # Modified field name
            'name': 'tax_state',
            'displayName': 'Tax Lot State',
            'related': True
        }, {
            # Modified field name
            'name': 'tax_postal_code',
            'displayName': 'Tax Lot Postal Code',
            'type': 'number',
            'related': True
        }, {
            'name': 'number_properties',
            'displayName': 'Number Properties',
            'treeAggregationType': 'sum',
            'type': 'number',
            'related': True
        }, {
            'name': 'block_number',
            'displayName': 'Block Number',
            'type': 'number',
            'related': True
        }, {
            'name': 'district',
            'displayName': 'District',
            'related': True
        }
    ]

    extra_data_columns = Column.objects.filter(
        organization_id=request.GET['organization_id'],
        is_extra_data=True,
        extra_data_source__isnull=False
    )

    for c in extra_data_columns:
        columns.append({
            'name': c.column_name,
            'displayName': '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source]),
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
        {
            'name': 'jurisdiction_taxlot_identifier',
            'displayName': 'Tax Lot ID',
            'pinnedLeft': True,
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'primary',
            'displayName': 'Primary/Secondary',
            'related': True
        }, {
            # INCOMPLETE, FIELD DOESN'T EXIST
            'name': 'primary_tax_lot_id',
            'displayName': 'Primary Tax Lot ID',
            'type': 'number',
            'related': False
        }, {
            # FIELD DOESN'T EXIST
            'name': 'calculated_taxlot_ids',
            'displayName': 'Associated TaxLot IDs',
            'type': 'numberStr',
            'related': True
        }, {
            # INCOMPLETE, FIELD DOESN'T EXIST
            'name': 'associated_building_tax_lot_id',
            'displayName': 'Associated Building Tax Lot ID',
            'type': 'number',
            'related': False
        }, {
            'name': 'address',
            'displayName': 'Tax Lot Address',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'city',
            'displayName': 'Tax Lot City',
            'related': False
        }, {
            'name': 'address_line_1',
            'displayName': 'Property Address 1',
            'type': 'numberStr',
            'related': True
        }, {
            # Modified field name
            'name': 'property_city',
            'displayName': 'Property City',
            'related': True
        }, {
            'name': 'property_name',
            'displayName': 'Property Name',
            'related': True
        }, {
            'name': 'jurisdiction_property_identifier',
            'displayName': 'Property / Building ID',
            'type': 'numberStr',
            'related': True
        }, {
            'name': 'building_portfolio_manager_identifier',
            'displayName': 'PM Property ID',
            'type': 'number',
            'related': True
        }, {
            'name': 'campus',
            'displayName': 'Campus',
            'type': 'boolean',
            'related': True
        }, {
            # INCOMPLETE, FIELD DOESN'T EXIST
            'name': 'pm_parent_property_id',
            'displayName': 'PM Parent Property ID',
            'type': 'numberStr',
            'related': False
        }, {
            'name': 'gross_floor_area',
            'displayName': 'Property Floor Area',
            'type': 'number',
            'related': True
        }, {
            'name': 'use_description',
            'displayName': 'Property Type',
            'related': True
        }, {
            'name': 'energy_score',
            'displayName': 'ENERGY STAR Score',
            'type': 'number',
            'related': True
        }, {
            'name': 'site_eui',
            'displayName': 'Site EUI (kBtu/sf-yr)',
            'type': 'number',
            'related': True
        }, {
            'name': 'property_notes',
            'displayName': 'Property Notes',
            'related': True
        }, {
            'name': 'year_ending',
            'displayName': 'Benchmarking year',
            'related': True
        }, {
            'name': 'owner',
            'displayName': 'Owner',
            'related': True
        }, {
            'name': 'owner_email',
            'displayName': 'Owner Email',
            'related': True
        }, {
            'name': 'owner_telephone',
            'displayName': 'Owner Telephone',
            'related': True
        }, {
            'name': 'address_line_2',
            'displayName': 'Property Address 2',
            'type': 'numberStr',
            'related': True
        }, {
            # Modified field name
            'name': 'property_state',
            'displayName': 'Property State',
            'related': True
        }, {
            # Modified field name
            'name': 'property_postal_code',
            'displayName': 'Property Postal Code',
            'type': 'number',
            'related': True
        }, {
            'name': 'building_count',
            'displayName': 'Number of Buildings',
            'type': 'number',
            'related': True
        }, {
            'name': 'year_built',
            'displayName': 'Year Built',
            'related': True
        }, {
            'name': 'recent_sale_date',
            'displayName': 'Property Sale Date',
            'related': True
        }, {
            'name': 'conditioned_floor_area',
            'displayName': 'Property Conditioned Floor Area',
            'type': 'number',
            'related': True
        }, {
            'name': 'occupied_floor_area',
            'displayName': 'Property Occupied Floor Area',
            'type': 'number',
            'related': True
        }, {
            'name': 'owner_address',
            'displayName': 'Owner Address',
            'type': 'numberStr',
            'related': True
        }, {
            'name': 'owner_city_state',
            'displayName': 'Owner City/State',
            'related': True
        }, {
            'name': 'owner_postal_code',
            'displayName': 'Owner Postal Code',
            'type': 'number',
            'related': True
        }, {
            'name': 'building_home_energy_score_identifier',
            'displayName': 'Home Energy Score ID',
            'type': 'numberStr',
            'related': True
        }, {
            'name': 'generation_date',
            'displayName': 'PM Generation Date',
            'related': True
        }, {
            'name': 'release_date',
            'displayName': 'PM Release Date',
            'related': True
        }, {
            'name': 'source_eui_weather_normalized',
            'displayName': 'Source EUI Weather Normalized',
            'type': 'number',
            'related': True
        }, {
            'name': 'site_eui_weather_normalized',
            'displayName': 'Site EUI Weather Normalized',
            'type': 'number',
            'related': True
        }, {
            'name': 'source_eui',
            'displayName': 'Source EUI',
            'type': 'number',
            'related': True
        }, {
            'name': 'energy_alerts',
            'displayName': 'Energy Alerts',
            'related': True
        }, {
            'name': 'space_alerts',
            'displayName': 'Space Alerts',
            'related': True
        }, {
            'name': 'building_certification',
            'displayName': 'Building Certification',
            'related': True
        }, {
            'name': 'state',
            'displayName': 'Tax Lot State',
            'related': False
        }, {
            'name': 'postal_code',
            'displayName': 'Tax Lot Postal Code',
            'type': 'number',
            'related': False
        }, {
            'name': 'number_properties',
            'displayName': 'Number Properties',
            'type': 'number',
            'related': False
        }, {
            'name': 'block_number',
            'displayName': 'Block Number',
            'related': False
        }, {
            'name': 'district',
            'displayName': 'District',
            'related': False
        }, {
            'name': 'lot_number',
            'displayName': 'Associated Tax Lot ID',
            'related': True
        }
    ]

    extra_data_columns = Column.objects.filter(
        organization_id=request.GET['organization_id'],
        is_extra_data=True,
        extra_data_source__isnull=False
    )

    for c in extra_data_columns:
        columns.append({
            'name': c.column_name,
            'displayName': '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source]),
            'related': c.extra_data_source == Column.SOURCE_PROPERTY,
            'source': Column.SOURCE_CHOICES_MAP[c.extra_data_source],
        })

    return columns
