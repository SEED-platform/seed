# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
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
        raise serializers.ValidationError(
            "Could not find value. Acceptable values are {0}.".format(list(self._choices.values())))
