"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import StatusLabel as Label


class LabelSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(
        source="super_organization",
        read_only=True,
    )
    is_applied = serializers.SerializerMethodField(
        help_text="IDs of the inventory views with the label (only when listing labels for inventory)"
    )
    is_applied_by_goal = serializers.SerializerMethodField(
        help_text="IDs of the property views the label was applied to by a goal (only when listing labels for properties)"
    )

    def __init__(self, *args, **kwargs):
        """
        Labels always exist in the context of the organization they are
        assigned to.  This serializer requires that the `super_organization`
        for the label be passed into the serializer during initialization so
        that uniqueness constraints involving the `super_organization` can be
        validated by the serializer. (It is only omitted when generating the API schema.)

        """
        super_organization = kwargs.pop("super_organization", None)
        super().__init__(*args, **kwargs)
        if super_organization is not None and getattr(self, "initial_data", None):
            # Copy the data, which is immutable for form-encoded requests
            self.initial_data = self.initial_data.copy()
            self.initial_data["super_organization"] = super_organization.pk

    class Meta:
        fields = (
            "id",
            "name",
            "color",
            "organization_id",
            "super_organization",
            "is_applied",
            "is_applied_by_goal",
            "show_in_list",
        )
        extra_kwargs = {
            "super_organization": {"write_only": True},
        }
        model = Label

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if "is_applied" not in dir(instance):
            del ret["is_applied"]

        if ret.get("is_applied_by_goal") is None:
            del ret["is_applied_by_goal"]

        return ret

    def get_is_applied(self, obj) -> list[int] | None:
        if "is_applied" not in dir(obj):
            return None

        elif obj.is_applied == [None]:
            return []

        else:
            return obj.is_applied

    def get_is_applied_by_goal(self, obj) -> list[int] | None:
        goal_applied = self.context.get("goal_applied_views")
        if goal_applied is None:
            return None

        return goal_applied.get(obj.id, [])
