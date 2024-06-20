# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers
from rest_framework.fields import ChoiceField

from seed.lib.uniformat.uniformat import uniformat_codes
from seed.models import Element, Uniformat


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
        if code not in uniformat_codes:
            raise serializers.ValidationError(f"Invalid Uniformat code '{code}'")
        return Uniformat.objects.only("id").get(code=code)

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
