"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import transaction
from rest_framework import serializers

from seed.models.data_views import DataView, DataViewParameter
from seed.models.filter_group import FilterGroup


class DataViewParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataViewParameter
        fields = "__all__"
        read_only_fields = ["data_view"]


class DataViewSerializer(serializers.ModelSerializer):
    parameters = DataViewParameterSerializer(many=True)
    filter_groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=FilterGroup.objects.all(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = DataView
        fields = ["id", "cycles", "filter_groups", "name", "organization", "parameters"]

    def validate(self, attrs):
        """Reject cycles, filter groups, or parameter columns of another organization"""
        org_id = getattr(attrs.get("organization", getattr(self.instance, "organization", None)), "id", None)
        related_objects = {
            "cycles": attrs.get("cycles") or [],
            "filter_groups": attrs.get("filter_groups") or [],
            "parameters": [parameter.get("column") for parameter in attrs.get("parameters") or []],
        }
        errors = {
            field: ["Must belong to the requested organization."]
            for field, objs in related_objects.items()
            if any(obj is not None and obj.organization_id != org_id for obj in objs)
        }
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            cycles = validated_data.pop("cycles")
            filter_groups = validated_data.pop("filter_groups", [])
            parameters = validated_data.pop("parameters")
            data_view = DataView.objects.create(**validated_data)
            data_view.cycles.set(cycles)
            data_view.filter_groups.set(filter_groups)

            for parameter in parameters:
                DataViewParameter.objects.create(data_view=data_view, **parameter)

            data_view.save()
            return data_view

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance.organization = validated_data.get("organization", instance.organization)
            instance.name = validated_data.get("name", instance.name)
            if "filter_groups" in validated_data:
                instance.filter_groups.set(validated_data["filter_groups"])
            if "cycles" in validated_data:
                instance.cycles.set(validated_data["cycles"])

            instance.save()

            # if new parameters are provided, delete previous ones so we can create the new params
            parameters_data = validated_data.get("parameters")
            if parameters_data:
                DataViewParameter.objects.filter(data_view=instance).delete()

                for parameter in parameters_data:
                    DataViewParameter.objects.create(data_view=instance, **parameter)

            return instance
