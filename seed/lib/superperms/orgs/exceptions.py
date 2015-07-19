"""
:copyright: (c) 2014 Building Energy Inc
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
