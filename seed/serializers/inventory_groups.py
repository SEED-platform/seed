# !/usr/bin/env python
from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import VIEW_LIST_INVENTORY_TYPE, InventoryGroup, InventoryGroupMapping, PropertyView, TaxLotView
from seed.serializers.access_level_instances import AccessLevelInstanceSerializer
from seed.serializers.base import ChoiceField


class InventoryGroupMappingSerializer(serializers.ModelSerializer):
    group_name = serializers.SerializerMethodField()

    class Meta:
        fields = ("id", "property_id", "taxlot_id", "group_id", "group_name")
        model = InventoryGroupMapping

    def get_group_name(self, obj):
        return obj.group.name


class InventoryGroupSerializer(serializers.ModelSerializer):
    inventory_type = ChoiceField(choices=VIEW_LIST_INVENTORY_TYPE)
    access_level_instance_data = AccessLevelInstanceSerializer(source="access_level_instance", many=False, read_only=True)

    def __init__(self, *args, **kwargs):
        if "inventory" not in kwargs:
            super().__init__(*args, **kwargs)
            return
        self.inventory = kwargs.pop("inventory")
        self.group_id = kwargs.pop("group_id")
        self.inventory_type = kwargs.pop("inventory_type")
        super().__init__(*args, **kwargs)

    class Meta:
        model = InventoryGroup
        fields = ("id", "name", "inventory_type", "access_level_instance", "access_level_instance_data", "organization")

    def to_representation(self, obj):
        result = super().to_representation(obj)
        inventory_list, views_list = self.get_member_list(obj)
        result["inventory_list"] = inventory_list
        result["views_list"] = views_list
        return result

    def get_member_list(self, obj):
        inventory_lookup = {0: ("property", PropertyView), 1: ("taxlot", TaxLotView)}
        inventory_type, view_class = inventory_lookup[obj.inventory_type]

        inventory = obj.group_mappings.all().values_list(inventory_type, flat=True)
        views = view_class.objects.filter(**{f"{inventory_type}__in": inventory}).values_list("id", flat=True)

        return list(inventory), list(views)

    def update(self, instance, validated_data):
        instance.__dict__.update(**validated_data)
        instance.save()

        return instance

    def create(self, validated_data):
        q = InventoryGroup.objects.create(**validated_data)
        q.save()
        return q

    def validate(self, data):
        if InventoryGroup.objects.filter(organization=data["organization"], name=data["name"]):
            raise ValidationError("Inventory Group Name must be unique.")
        return data
