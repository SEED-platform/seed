# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
import json
from json import load
import logging
import pint

from django.core.paginator import EmptyPage, Paginator
from lxml import etree 
from lxml.builder import E
from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    Organization,
    OrganizationUser,
)
from seed.lib.xml_mapping.mapper import default_buildingsync_profile_mappings
from seed.models import Column, ColumnMappingProfile, PropertyState, TaxLotState
from seed.models.data_quality import DataQualityCheck


def default_pm_mappings():
    with open("./seed/lib/mappings/data/pm-mapping.json", "r") as read_file:
        raw_mappings = load(read_file)

    # Verify that from_field values are all uniq
    from_fields = [rm['from_field'] for rm in raw_mappings]
    assert len(from_fields) == len(set(from_fields))

    # taken from mapping partial (./static/seed/partials/mapping.html)
    valid_units = [
        # area units
        "ft**2",
        "m**2",
        # eui_units
        "kBtu/ft**2/year",
        "kWh/m**2/year",
        "GJ/m**2/year",
        "MJ/m**2/year",
        "kBtu/m**2/year",
    ]

    formatted_mappings = []

    # check unit value is one that SEED recognizes
    for rm in raw_mappings:
        from_units = rm.get('units', None)
        if from_units not in valid_units:
            from_units = None

        mapping = {
            "to_field": rm.get('to_field'),
            "from_field": rm.get('from_field'),
            "from_units": from_units,
            "to_table_name": rm.get('to_table_name'),
        }

        formatted_mappings.append(mapping)

    return formatted_mappings


def _create_default_columns(organization_id):
    """
    Create the default list of columns for an organization

    :param organization_id: int, ID of the organization object
    :return: None
    """
    for column in Column.DATABASE_COLUMNS:
        details = {
            'organization_id': organization_id,
        }
        details.update(column)

        original_identity_fields = [
            'custom_id_1',
            'pm_property_id',
            'jurisdiction_tax_lot_id',
            'ubid',
        ]

        # Default fields and order are those used before customization was enabled
        default_geocoding_fields = [
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
        ]

        column_name = column.get('column_name')

        if column_name in original_identity_fields:
            details['is_matching_criteria'] = True

        try:
            field_index = default_geocoding_fields.index(column_name)
            # Increment each index by 1 since 0 represents a geocoding deactivated field.
            details['geocoding_order'] = field_index + 1
        except ValueError:
            pass

        Column.objects.create(**details)


def create_organization(user=None, org_name='test_org', *args, **kwargs):
    """
    Helper script to create a user/org relationship from scratch. This is heavily used and
    creates the default labels, columns, and data quality rules when a new organization is created

    :param user: user inst.
    :param org_name: str, name of Organization we'd like to create.
    :param (optional) kwargs: 'role', int; 'status', str.
    """
    from seed.models import StatusLabel as Label
    organization_user = None
    user_added = False

    organization = Organization.objects.create(
        name=org_name
    )

    if user:
        organization_user, user_added = OrganizationUser.objects.get_or_create(
            user=user, organization=organization, access_level_instance=organization.root
        )

    for label in Label.DEFAULT_LABELS:
        Label.objects.get_or_create(
            name=label,
            super_organization=organization,
            defaults={'color': 'blue'},
        )

    # upon initializing a new organization (SuperOrganization), create
    # the default columns
    _create_default_columns(organization.id)

    # ... and the default column mapping profile for Portfolio Manager
    organization.columnmappingprofile_set.create(
        name='Portfolio Manager Defaults',
        mappings=default_pm_mappings()
    )

    # ... and the default column mapping profile for BuildingSync
    organization.columnmappingprofile_set.create(
        name='BuildingSync v2.0 Defaults',
        mappings=default_buildingsync_profile_mappings(),
        profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT
    )

    # create the default rules for this organization
    DataQualityCheck.retrieve(organization.id)

    return organization, organization_user, user_added


def create_suborganization(user, current_org, suborg_name='', user_role=ROLE_MEMBER):
    # Create the suborg manually to prevent the generation of the default columns, labels, and data
    # quality checks

    if Organization.objects.filter(name=suborg_name, parent_org=current_org).exists():
        sub_org = Organization.objects.filter(name=suborg_name, parent_org=current_org).first()
    else:
        sub_org = Organization.objects.create(name=suborg_name)

        # upon initializing an organization, create the default columns
        _create_default_columns(sub_org.id)

    ou, _ = OrganizationUser.objects.get_or_create(user=user, organization=sub_org, access_level_instance=sub_org.root)
    ou.role_level = user_role
    ou.save()

    sub_org.parent_org = current_org

    try:
        sub_org.save()
    except TooManyNestedOrgs:
        sub_org.delete()
        return False, 'Tried to create child of a child organization.', None

    return True, sub_org, ou


def public_feed(org, request):
    """
    Format all property and taxlot state data to be displayed on a public feed
    """
    params = request.query_params
    page = get_int(params.get('page'), 1)
    per_page = get_int(params.get('per_page'), 100)
    property_key = params.get('property_key', 'pm_property_id')
    taxlot_key = params.get('taxlot_key', 'jurisdiction_tax_lot_id')
    pstates = get_states(
        PropertyState,
        org.propertystate_set.filter(propertyview__isnull=False),
        property_key,
        page,
        per_page
    )
    tstates = get_states(
        TaxLotState,
        org.taxlotstate_set.filter(taxlotview__isnull=False),
        taxlot_key,
        page,
        per_page
    )

    metadata = {
        'organization': org.name,
        'organization_id': org.id,
        'page': page,
        'per_page': per_page,
        'total_pages': int((len(pstates) + len(tstates)) / per_page) + 1,
        'properties': len(pstates),
        'taxlots': len(tstates),
        'property_key': property_key,
        'taxlot_key': taxlot_key,
    }

    # gonna need public columns for properties and taxlots
    p_public_columns = Column.objects.filter(shared_field_type=1, table_name='PropertyState').values_list('column_name', 'is_extra_data')
    t_public_columns = Column.objects.filter(shared_field_type=1, table_name='TaxLotState').values_list('column_name', 'is_extra_data')
    data = {'properties': {}, 'taxlots': {}}
    for pstate in pstates:
        # what if matching criteria dne? a whole bunch of None's
        add_state_to_data(data['properties'], pstate.propertyview_set.first(), pstate, property_key, p_public_columns)

    for tstate in tstates:
        add_state_to_data(data['taxlots'], tstate.taxlotview_set.first(), tstate, taxlot_key, t_public_columns)

    return {'metadata': metadata, 'data': data}

def add_state_to_data(data, view, state, key, public_columns):
    # add public_column state data to the response
    cycle = view.cycle.name
    matching_field = getattr(state, key, None)
    property_data = data.setdefault(matching_field, {})
    cycle_data = property_data.setdefault(cycle, {})

    for (name, extra_data) in public_columns:
        if not extra_data:
            value = getattr(state, name, None)
        else:
            value = state.extra_data.get(name, None)

        if isinstance(value, pint.Quantity):
            # convert pint to string with units
            # json cant display exponents.
            # value = "{:~P}".format(value)
            value = f'{value.m} {value.u}'

        cycle_data[name] = value


def get_int(value, default):
    try: 
        result = int(float(value))
        return result if result > 0 else default
    except (ValueError, TypeError):
        return default

def get_states(cls, query, key, page, per_page):
    # determine if key is cannonical or extra_data
    fields = [field.name for field in cls._meta.get_fields()]
    extra_data = True if key not in fields else False
    order_key = key if not extra_data else f'extra_data__{key}'
    # Django's natural order is by cycle, we need to order by the matching key
    states = query.order_by(order_key)
    
    paginator = Paginator(states, per_page)
    try: 
        return paginator.page(page)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


######### MORE OF AN RSS LIST ###########
def public_feed_rss(org, request):
    """
    Format all property and taxlot state data to be displayed on a public feed
    """
    base_url = request.build_absolute_uri('/')
    params = request.query_params
    page = get_int(params.get('page'), 1)
    per_page = get_int(params.get('per_page'), 100)
    property_key = params.get('property_key', 'pm_property_id')
    taxlot_key = params.get('taxlot_key', 'jurisdiction_tax_lot_id')
    pstates = get_states(
        PropertyState,
        org.propertystate_set.filter(propertyview__isnull=False),
        property_key,
        page,
        per_page
    )
    tstates = get_states(
        TaxLotState,
        org.taxlotstate_set.filter(taxlotview__isnull=False),
        taxlot_key,
        page,
        per_page
    )

    p_public_columns = Column.objects.filter(shared_field_type=1, table_name='PropertyState').values_list('column_name', 'is_extra_data')
    t_public_columns = Column.objects.filter(shared_field_type=1, table_name='TaxLotState').values_list('column_name', 'is_extra_data')
    data = []

    for pstate in pstates:
        # what if matching criteria dne? a whole bunch of None's
        add_state_to_data_rss(data, 'property', pstate.propertyview_set.first(), pstate, p_public_columns)

    for tstate in tstates:
        add_state_to_data_rss(data, 'taxlot', tstate.taxlotview_set.first(), tstate, t_public_columns)

    return convert_json_to_rss(org, data, base_url, property_key, taxlot_key)

def add_state_to_data_rss(data, type, view, state, public_columns):
    # add public_column state data to the response
    datum = {
        'type': type,
        'cycle': view.cycle.name,
        'id': view.id
    }

    for (name, extra_data) in public_columns:
        if not extra_data:
            value = getattr(state, name, None)
        else:
            value = state.extra_data.get(name, None)

        if isinstance(value, pint.Quantity):
            # convert pint to string with units
            # json cant display exponents.
            value = f'{value.m} {value.u}'

        datum[name] = value
    data.append(datum)

def convert_json_to_rss(org, json_data, base_url, property_key, taxlot_key):
    rss = E.rss(
        E.channel(
            E.title('SEED Property and TaxLot Updates'),
            E.link(f'{base_url}'),
            E.description(f'Recent updates to SEED organization {org}'),
            *[E.item(
                E.title(f'{entry["type"].capitalize()} {entry.get(property_key, None) if entry["type"] == "property" else entry.get(taxlot_key, None)}'),
                E.link(f'{base_url}app/#/{"properties" if entry["type"] == "property" else "taxlots"}/{entry["id"]}'),
                E.description(json.dumps(entry))

            ) for entry in json_data]
        ),
        version="1.0"
    )
    
    rss_xml = etree.tostring(rss, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    return rss_xml
