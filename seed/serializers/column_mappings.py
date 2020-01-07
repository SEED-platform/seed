#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from rest_framework import serializers

from seed.models import ColumnMapping
from seed.serializers.columns import ColumnSerializer


class ColumnMappingSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(source='super_organization',
                                                         read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)

    class Meta:
        model = ColumnMapping
        exclude = ('source_type', 'column_raw', 'column_mapped')

    def to_representation(self, obj):
        """Return only the first items in the column_raw and column_mapped"""
        result = super().to_representation(obj)

        if obj.column_raw and obj.column_raw.first():
            result['column_raw'] = ColumnSerializer(obj.column_raw.first()).data

        if obj.column_mapped and obj.column_mapped.first():
            result['column_mapped'] = ColumnSerializer(obj.column_mapped.first()).data

        return result
