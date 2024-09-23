"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers
from rest_framework.fields import ChoiceField

from seed.lib.tkbl.tkbl import tkbl_data
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
        if not isinstance(extra_data, dict):
            raise serializers.ValidationError("Only flat JSON objects are allowed")

        for key, val in extra_data.items():
            if isinstance(val, (dict, list)):
                raise serializers.ValidationError("Nested structures are not allowed")

        return extra_data

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


class ElementPropertyTKBLSerializer(ElementPropertySerializer):
    tkbl = serializers.SerializerMethodField()

    def get_tkbl(self, element):
        return {
            "estcp": tkbl_data["estcp"].get(element.code.code, []),
            "sftool": tkbl_data["sftool"].get(element.code.code, []),
        }
