"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django_otp import devices_for_user
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers

from seed.landing.models import SEEDUser as User
from seed.views.main import _get_default_org as get_default_org_for_user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "api_key", "is_superuser", "id", "pk")

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        two_factor_devices = list(devices_for_user(instance))
        if two_factor_devices and isinstance(two_factor_devices[0], EmailDevice):
            ret["two_factor_method"] = "email"
        elif two_factor_devices and isinstance(two_factor_devices[0], TOTPDevice):
            ret["two_factor_method"] = "token"
        else:
            ret["two_factor_method"] = "disabled"

        additional_fields = dict(
            list(
                zip(
                    ("org_id", "org_name", "org_role", "ali_name", "ali_id", "is_ali_root", "is_ali_leaf", "org_user_id", "settings"),
                    get_default_org_for_user(instance),
                )
            )
        )
        for k, v in additional_fields.items():
            ret[k] = v

        return ret
