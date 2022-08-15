# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models import VIEW_LIST_INVENTORY_TYPE, FilterGroup
from seed.models.filter_group import LABEL_LOGIC_TYPE


class FilterGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterGroup
        fields = ('name', 'query_dict', 'inventory_type', 'id', "organization_id", "labels", "label_logic")
        extra_kwargs = {
            'user': {'read_only': True},
            'organization': {'read_only': True},
            'organization_id': {'read_only': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret["inventory_type"] = VIEW_LIST_INVENTORY_TYPE[ret["inventory_type"]][1]
        ret["label_logic"] = LABEL_LOGIC_TYPE[ret["label_logic"]][1]
        ret["labels"] = sorted(ret["labels"])

        return ret
