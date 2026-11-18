"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from seed.models import VIEW_LIST_INVENTORY_TYPE, InventoryGroup, InventoryGroupMapping, PropertyView, TaxLotView
from seed.serializers.access_level_instances import AccessLevelInstanceSerializer
from seed.serializers.base import ChoiceField
from seed.serializers.systems import SystemSerializer

logger = logging.getLogger(__name__)


class InventoryGroupMappingSerializer(serializers.ModelSerializer):
    group_name = serializers.SerializerMethodField()

    class Meta:
        fields = ("id", "property_id", "taxlot_id", "group_id", "group_name")
        model = InventoryGroupMapping

    def get_group_name(self, obj) -> str:
        return obj.group.name


class InventoryGroupSerializer(serializers.ModelSerializer):
    inventory_type = ChoiceField(choices=VIEW_LIST_INVENTORY_TYPE)
    access_level_instance_data = AccessLevelInstanceSerializer(source="access_level_instance", many=False, read_only=True)
    systems = serializers.SerializerMethodField()

    # `SystemSerializer` is polymorphic (DES, EVSE, battery), so its fields vary by system type
    @extend_schema_field({"type": "array", "items": {"type": "object"}})
    def get_systems(self, obj):
        return SystemSerializer(obj.systems.all().select_subclasses(), many=True).data

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
        fields = ("id", "name", "inventory_type", "access_level_instance", "access_level_instance_data", "organization", "systems")

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
        groups = InventoryGroup.objects.filter(organization=data["organization"], name=data["name"])
        if self.instance is not None:
            groups = groups.exclude(pk=self.instance.pk)
        if groups.exists():
            raise ValidationError("Inventory Group Name must be unique.")
        return data


# Schema only: also documents the members that `InventoryGroupSerializer.to_representation` adds
class InventoryGroupResponseSerializer(InventoryGroupSerializer):
    inventory_list = serializers.ListField(child=serializers.IntegerField(), read_only=True, help_text="IDs of the properties or tax lots")
    views_list = serializers.ListField(child=serializers.IntegerField(), read_only=True, help_text="IDs of their property or tax lot views")

    class Meta(InventoryGroupSerializer.Meta):
        fields = (*InventoryGroupSerializer.Meta.fields, "inventory_list", "views_list")
