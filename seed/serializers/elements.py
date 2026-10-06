"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import Counter

from rest_framework import serializers
from rest_framework.fields import ChoiceField

from seed.lib.uniformat.uniformat import uniformat_codes
from seed.models import Element, Uniformat


def validate_flat_extra_data(extra_data) -> dict:
    """Restrict element extra data to a flat JSON object."""
    if not isinstance(extra_data, dict):
        raise serializers.ValidationError("Only flat JSON objects are allowed")

    for value in extra_data.values():
        if isinstance(value, (dict, list)):
            raise serializers.ValidationError("Nested structures are not allowed")

    return extra_data


class ElementBulkListSerializer(serializers.ListSerializer):
    def validate(self, data):
        element_ids = [element["id"] for element in data]
        duplicate_ids = sorted(element_id for element_id, count in Counter(element_ids).items() if count > 1)
        if duplicate_ids:
            raise serializers.ValidationError(f"Duplicate element IDs: {duplicate_ids}")
        return data


class ElementBulkSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(min_value=1)
    id = serializers.CharField(max_length=36)
    code = ChoiceField(choices=uniformat_codes)
    description = serializers.CharField(required=False, allow_null=True)
    installation_date = serializers.DateField(required=False, allow_null=True)
    condition_index = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=100)
    remaining_service_life = serializers.FloatField(required=False, allow_null=True)
    replacement_cost = serializers.FloatField(required=False, allow_null=True, min_value=0)
    manufacturing_date = serializers.DateField(required=False, allow_null=True)
    extra_data = serializers.JSONField(required=False, default=dict, validators=[validate_flat_extra_data])

    class Meta:
        list_serializer_class = ElementBulkListSerializer


class ElementSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(
        model_field=Element._meta.get_field("element_id"), help_text=Element._meta.get_field("element_id").help_text
    )
    code = serializers.SerializerMethodField()

    class Meta:
        model = Element
        exclude = ["element_id", "organization"]

    def get_code(self, element):
        return element.code.code


class ElementPropertySerializer(ElementSerializer):
    code = ChoiceField(choices=uniformat_codes)

    class Meta(ElementSerializer.Meta):
        exclude = [*ElementSerializer.Meta.exclude, "property"]

    def validate_code(self, code: str) -> Uniformat:
        """
        Validator that restricts code to only valid Uniformat values
        """
        if code not in uniformat_codes:
            raise serializers.ValidationError(f"Invalid Uniformat code '{code}'")
        return Uniformat.objects.only("id").get(code=code)

    def validate_extra_data(self, extra_data) -> dict:
        """
        Validator that restricts extra_data to only key-value pairs and disallows nested structures
        """
        return validate_flat_extra_data(extra_data)

    def create(self, validated_data):
        validated_data["organization_id"] = self.context["request"].query_params["organization_id"]
        validated_data["property_id"] = self.context["request"].parser_context["kwargs"]["property_pk"]
        validated_data["element_id"] = validated_data.pop("id", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["organization_id"] = self.context["request"].query_params["organization_id"]
        validated_data["property_id"] = self.context["request"].parser_context["kwargs"]["property_pk"]
        validated_data["element_id"] = validated_data.pop("id", None)
        return super().update(instance, validated_data)
