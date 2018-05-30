# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.apps import apps

from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.models import Column


def create_organization(user=None, org_name='', *args, **kwargs):
    """Helper script to create a user/org relationship from scratch.

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
    for column in Column.DATABASE_COLUMNS:
        details = {
            'organization_id': organization.id,
        }
        details.update(column)
        Column.objects.create(**details)

    # create the default rules for this organization
    apps.get_model('seed', 'DataQualityCheck').retrieve(organization)

    return organization, organization_user, user_added
