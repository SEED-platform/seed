# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER


def get_js_role(role):
    """return the JS friendly role name for user
    :param role: role as defined in superperms.models
    :returns: (string) JS role name
    """
    roles = {
        ROLE_OWNER: "owner",
        ROLE_VIEWER: "viewer",
        ROLE_MEMBER: "member",
    }
    return roles.get(role, "viewer")


def get_role_from_js(role):
    """return the OrganizationUser role_level from the JS friendly role name

    :param role: 'member', 'owner', or 'viewer'
    :returns: int role as defined in superperms.models
    """
    roles = {
        "owner": ROLE_OWNER,
        "viewer": ROLE_VIEWER,
        "member": ROLE_MEMBER,
    }
    return roles[role]
