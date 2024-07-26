# !/usr/bin/env python
# encoding: utf-8
from rest_framework import serializers

from seed.models import (
    VIEW_LIST_INVENTORY_TYPE,
    InventoryGroup,
    InventoryGroupMapping
)
from seed.serializers.base import ChoiceField


class InventoryGroupMappingSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            "id",
            "property_id",
            "tax_lot_id",
            "group_id"
        )
        model = InventoryGroupMapping


class InventoryGroupSerializer(serializers.ModelSerializer):
    inventory_type = ChoiceField(choices=VIEW_LIST_INVENTORY_TYPE)
    member_list = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        if 'inventory' not in kwargs:
            super().__init__(*args, **kwargs)
            return
        self.inventory = kwargs.pop('inventory')
        self.group_id = kwargs.pop('group_id')
        self.inventory_type = kwargs.pop('inventory_type')
        super().__init__(*args, **kwargs)

    class Meta:
        model = InventoryGroup
        fields = (
            'id',
            'name',
            'inventory_type',
            'organization',
            'member_list'
        )

    def get_member_list(self, obj):
        filtered_result = []
        if hasattr(self, 'inventory'):
            if self.inventory_type == 0:
                filtered_result = InventoryGroupMapping.objects.filter(group=self.group_id).filter(
                    property__in=self.inventory).values_list('property', flat=True)
            elif self.inventory_type == 1:
                filtered_result = InventoryGroupMapping.objects.filter(group=self.group_id).filter(
                    tax_lot__in=self.inventory).values_list('tax_lot', flat=True)
        return filtered_result

    def update(self, instance, validated_data):
        instance.__dict__.update(**validated_data)
        instance.save()

        return instance

    def create(self, validated_data):
        q = InventoryGroup.objects.create(**validated_data)
        q.save()
        return q
