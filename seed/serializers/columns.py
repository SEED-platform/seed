#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

:author Fable Turas <fable@raintechpdx.com>
"""

from rest_framework import serializers

from seed.models import Column
from seed.serializers.base import ChoiceField


class ColumnSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(source='organization', read_only=True)
    unit_name = serializers.SlugRelatedField(source='unit', slug_field='unit_name', read_only=True)
    unit_type = serializers.SlugRelatedField(source='unit', slug_field='unit_type', read_only=True)

    merge_protection = ChoiceField(choices=Column.COLUMN_MERGE_PROTECTION, default='Favor New')

    class Meta:
        model = Column
        fields = (
            'id', 'organization_id', 'table_name', 'merge_protection',
            'column_name', 'is_extra_data', 'unit_name', 'unit_type'
        )
