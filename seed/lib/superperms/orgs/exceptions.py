"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""


class TooManyNestedOrgsError(Exception):
    """We only support one level of nesting."""


class UserNotInOrganizationError(Exception):
    """Raised when a user does not exist, or does not belong to an org."""


class InsufficientPermissionError(Exception):
    """Raised when a user attempts an action for which they're not allowed."""
