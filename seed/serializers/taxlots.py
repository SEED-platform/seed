# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    TaxLot, TaxLotProperty, TaxLotState, TaxLotView,
)


class TaxLotLabelsField(serializers.RelatedField):

    def to_representation(self, value):
        return value.id


class TaxLotSerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = TaxLotLabelsField(read_only=True, many=True)

    class Meta:
        model = TaxLot


class TaxLotPropertySerializer(serializers.ModelSerializer):

    class Meta:
        model = TaxLotProperty


class TaxLotStateSerializer(serializers.ModelSerializer):
    extra_data = serializers.JSONField()

    class Meta:
        model = TaxLotState


class TaxLotViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaxLotView
        depth = 1
