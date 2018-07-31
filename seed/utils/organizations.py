# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
    ROLE_MEMBER
)
from seed.models import Column
from seed.models.data_quality import DataQualityCheck


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
        Column.objects.create(**details)


def create_organization(user=None, org_name='', *args, **kwargs):
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
            user=user, organization=organization
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

    # create the default rules for this organization
    DataQualityCheck.retrieve(organization.id)

    return organization, organization_user, user_added


def create_suborganization(user, current_org, suborg_name='', user_role=ROLE_MEMBER):
    # Create the suborg manually to prevent the generation of the default columns, labels, and data
    # quality checks

    if Organization.objects.filter(name=suborg_name).exists():
        sub_org = Organization.objects.filter(name=suborg_name).first()
    else:
        sub_org = Organization.objects.create(name=suborg_name)

        # upon initializing an organization, create the default columns
        _create_default_columns(sub_org.id)

    ou, _ = OrganizationUser.objects.get_or_create(user=user, organization=sub_org)
    ou.role_level = user_role
    ou.save()

    sub_org.parent_org = current_org

    try:
        sub_org.save()
    except TooManyNestedOrgs:
        sub_org.delete()
        return False, 'Tried to create child of a child organization.'

    return True, sub_org, ou
