# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Paul Munday <paul@paulmunday.net>
"""
from rest_framework import serializers

from seed.models import Property
from seed.serializers.properties import (
    PropertyLabelsField,
    PropertyListSerializer,
    PropertyMinimalSerializer
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
