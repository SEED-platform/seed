"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.lib.superperms.orgs.models import ROLE_OWNER
from seed.models import OrganizationUser


class OrganizationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUser
        fields = ["settings", "role_level", "status", "organization", "user"]

    def validate_organization(self, organization):
        # The access level instance belongs to the current organization
        if self.instance is not None and organization != self.instance.organization:
            raise serializers.ValidationError("Organization users cannot be moved to another organization.")
        return organization

    def validate_role_level(self, role_level):
        if (
            role_level == ROLE_OWNER
            and self.instance is not None
            and self.instance.access_level_instance != self.instance.organization.root
        ):
            raise serializers.ValidationError("Owners must be member of the organization's root.")
        return role_level

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["email"] = instance.user.email
        result["first_name"] = instance.user.first_name
        result["last_name"] = instance.user.last_name
        return result
