# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import VIEW_LIST_INVENTORY_TYPE, FilterGroup


class FilterGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterGroup
        fields = ('name', 'query_dict', 'inventory_type', 'id', 'organization_id', 'and_labels', 'or_labels', 'exclude_labels')
        extra_kwargs = {'user': {'read_only': True}, 'organization': {'read_only': True}, 'organization_id': {'read_only': True}}

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret['inventory_type'] = VIEW_LIST_INVENTORY_TYPE[ret['inventory_type']][1]
        ret['and_labels'] = sorted(ret['and_labels'])
        ret['or_labels'] = sorted(ret['or_labels'])
        ret['exclude_labels'] = sorted(ret['exclude_labels'])

        return ret
