# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""


class TooManyNestedOrgs(Exception):
    """We only support one level of nesting."""


class UserNotInOrganization(Exception):
    """Raised when a user does not exist, or does not belong to an org."""


class InsufficientPermission(Exception):
    """Raised when a user attempts an action for which they're not allowed."""
