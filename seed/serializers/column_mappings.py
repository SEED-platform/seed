#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from rest_framework import serializers

from seed.models import ColumnMapping
from seed.serializers.columns import ColumnSerializer


# from seed.serializers.base import ChoiceField


class ColumnMappingSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(source='super_organization',
                                                         read_only=True)
    column_raw = ColumnSerializer()
    column_mapped = ColumnSerializer()

    class Meta:
        model = ColumnMapping
        exclude = ('source_type',)
