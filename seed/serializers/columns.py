#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

:author Fable Turas <fable@raintechpdx.com>
"""

from rest_framework import serializers

from seed.models import Column
from seed.serializers.base import ChoiceField


class ColumnSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('concat_name')
    organization_id = serializers.PrimaryKeyRelatedField(source='organization', read_only=True)
    unit_name = serializers.SlugRelatedField(source='unit', slug_field='unit_name', read_only=True)
    unit_type = serializers.SlugRelatedField(source='unit', slug_field='unit_type', read_only=True)

    merge_protection = ChoiceField(choices=Column.COLUMN_MERGE_PROTECTION, default='Favor New')
    shared_field_type = ChoiceField(choices=Column.SHARED_FIELD_TYPES)

    class Meta:
        model = Column
        fields = (
            'id', 'name', 'organization_id', 'table_name', 'merge_protection', 'shared_field_type',
            'column_name', 'is_extra_data', 'unit_name', 'unit_type', 'display_name', 'data_type',
            'is_matching_criteria', 'geocoding_order', 'recognize_empty',
        )

    def concat_name(self, obj):
        """
        set the name of the column which is a special field because it can take on a
        relationship with the table_name and have an _extra associated with it
        """
        return '%s_%s' % (obj.column_name, obj.id)
