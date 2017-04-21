# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from seed.lib.superperms.orgs.models import (
    Organization as SuperOrganization,
    OrganizationUser as SuperOrganizationUser
)


def create_organization(user, org_name='', *args, **kwargs):
    """Helper script to create a user/org relationship from scratch.

    :param user: user inst.
    :param org_name: str, name of Organization we'd like to create.
    :param (optional) kwargs: 'role', int; 'status', str.

    """
    from seed.models import (
        StatusLabel as Label,
    )
    org = SuperOrganization.objects.create(
        name=org_name
    )
    org_user, user_added = SuperOrganizationUser.objects.get_or_create(
        user=user, organization=org
    )

    for label in Label.DEFAULT_LABELS:
        Label.objects.get_or_create(
            name=label,
            super_organization=org,
            defaults={'color': 'blue'},
        )

    return org, org_user, user_added
