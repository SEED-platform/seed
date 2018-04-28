# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
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
    org_user = None
    user_added = False

    org = Organization.objects.create(
        name=org_name
    )

    if user:
        org_user, user_added = OrganizationUser.objects.get_or_create(
            user=user, organization=org
        )

    for label in Label.DEFAULT_LABELS:
        Label.objects.get_or_create(
            name=label,
            super_organization=org,
            defaults={'color': 'blue'},
        )

    # upon initializing a new organization (SuperOrganization), create
    # the default columns
    for column in Column.DEFAULT_COLUMNS:
        details = {
            'organization_id': org.id,
        }
        details.update(column)
        Column.objects.create(**details)

    return org, org_user, user_added
