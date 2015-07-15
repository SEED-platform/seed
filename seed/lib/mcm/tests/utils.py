"""
:copyright: (c) 2014 Building Energy Inc
"""


def list_has_substring(substring, l):
    """Return True if substring occurs in list l."""
    found_substring = False
    for item in l:
        if substring in item:
            found_substring = True
            break

    return found_substring


class FakeManager(object):
    def get_or_create(*args, **kwargs):
        return FakeModel(), True


class FakeModel(object):
    """Used for testing purposes, only."""
    property_name = ''
    objects = FakeManager()

    def save(self):
        pass
