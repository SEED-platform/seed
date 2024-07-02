# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import contextlib
from typing import Any, Optional

from django.db import ProgrammingError
from rest_framework import serializers

from seed.models import Uniformat


class UniformatSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(model_field=Uniformat._meta.get_field("code"), help_text=Uniformat._meta.get_field("code").help_text)
    parent = serializers.SerializerMethodField(
        help_text="If applicable, the higher-level Uniformat category that the current category is a child of"
    )

    class Meta:
        model = Uniformat
        exclude = ["code"]

    # Initialize Uniformat lookup once on Django launch
    # Note: this is allowed to fail when performing the initial migrate on an empty database
    with contextlib.suppress(ProgrammingError):
        code_lookup: dict[str, str] = {obj["id"]: obj["code"] for obj in Uniformat.objects.values("id", "code")}

    def get_parent(self, uniformat) -> Optional[str]:
        return self.code_lookup[uniformat.parent_id] if uniformat.parent_id else None


class UniformatChildSerializer(UniformatSerializer):
    children = serializers.SerializerMethodField(help_text="Sub-categories of the specified Uniformat category")

    def get_children(self, uniformat) -> list[dict[str, Any]]:
        children = Uniformat.objects.filter(code__startswith=uniformat.code).exclude(code=uniformat.code).order_by("code")
        return UniformatSerializer(children, many=True).data
