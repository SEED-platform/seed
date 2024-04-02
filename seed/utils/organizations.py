# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import locale
from json import load

from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.lib.superperms.orgs.models import ROLE_MEMBER, Organization, OrganizationUser
from seed.lib.xml_mapping.mapper import default_buildingsync_profile_mappings
from seed.models import Column, ColumnMappingProfile
from seed.models.data_quality import DataQualityCheck


def default_pm_mappings():
    with open('./seed/lib/mappings/data/pm-mapping.json', encoding=locale.getpreferredencoding(False)) as read_file:
        raw_mappings = load(read_file)

    # Verify that from_field values are all uniq
    from_fields = [rm['from_field'] for rm in raw_mappings]
    assert len(from_fields) == len(set(from_fields))

    # taken from mapping partial (./static/seed/partials/mapping.html)
    valid_units = [
        # area units
        'ft**2',
        'm**2',
        # eui_units
        'kBtu/ft**2/year',
        'kWh/m**2/year',
        'GJ/m**2/year',
        'MJ/m**2/year',
        'kBtu/m**2/year',
    ]

    formatted_mappings = []

    # check unit value is one that SEED recognizes
    for rm in raw_mappings:
        from_units = rm.get('units', None)
        if from_units not in valid_units:
            from_units = None

        mapping = {
            'to_field': rm.get('to_field'),
            'from_field': rm.get('from_field'),
            'from_units': from_units,
            'to_table_name': rm.get('to_table_name'),
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

    organization = Organization.objects.create(name=org_name)

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
    organization.columnmappingprofile_set.create(name='Portfolio Manager Defaults', mappings=default_pm_mappings())

    # ... and the default column mapping profile for BuildingSync
    organization.columnmappingprofile_set.create(
        name='BuildingSync v2.0 Defaults',
        mappings=default_buildingsync_profile_mappings(),
        profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT,
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
