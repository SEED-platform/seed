# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""


class TooManyNestedOrgs(Exception):
    """We only support one level of nesting."""
    pass


class UserNotInOrganization(Exception):
    """Raised when a user doesn't exist, or doesn't belong to an org."""
    pass


class InsufficientPermission(Exception):
    """Raised when a user attempts an action for which they're not allowed."""
    pass
