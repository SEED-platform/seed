"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Paul Munday <paul@paulmunday.net>
"""

from collections import OrderedDict

from rest_framework import serializers


class ChoiceField(serializers.Field):
    def __init__(self, choices, **kwargs):
        """init."""
        self._choices = OrderedDict(choices)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        return self._choices[obj]

    def to_internal_value(self, data):
        for i in self._choices:
            if self._choices[i] == data:
                return i
        raise serializers.ValidationError(f"Could not find value. Acceptable values are {list(self._choices.values())}.")
