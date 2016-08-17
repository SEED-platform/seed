# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    TaxLotView, TaxLotState, TaxLotProperty
)
class TaxLotPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLotProperty


class TaxLotViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLotView
        depth = 1


class TaxLotStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxLotState
    extra_data = serializers.JSONField()
