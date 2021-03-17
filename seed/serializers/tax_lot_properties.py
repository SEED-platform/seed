# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""

from rest_framework import serializers

from seed.models import (
    Property
)
from seed.serializers.properties import (
    PropertyLabelsField,
    PropertyListSerializer,
    PropertyMinimalSerializer,
)


class TaxLotPropertySerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = PropertyLabelsField(read_only=True, many=True)

    class Meta:
        model = Property
        fields = '__all__'
        extra_kwargs = {
            'organization': {'read_only': True}
        }

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = PropertyMinimalSerializer()
        return PropertyListSerializer(*args, **kwargs)
