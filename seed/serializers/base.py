"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import OrderedDict

from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty

from seed.utils.encrypt import MAX_SECRET_LENGTH, decrypt_secret, encrypt_if_changed


class EncryptedSecretField(serializers.CharField):
    """
    A model field holding a secret encrypted by `seed.utils.encrypt`. It is represented in plaintext, and input is
    validated as plaintext and then encrypted. Submitting the represented value keeps the stored value.
    """

    def __init__(self, **kwargs):
        # Whitespace is significant in a password (keys and tokens can pass trim_whitespace=True)
        kwargs.setdefault("trim_whitespace", False)
        kwargs.setdefault("max_length", MAX_SECRET_LENGTH)
        super().__init__(**kwargs)

    def _context(self, instance) -> str:
        return f"{type(self.parent).__name__}.{self.field_name} pk={getattr(instance, 'pk', None)}"

    def get_attribute(self, instance):
        # Remember the instance being represented to identify an undecryptable value in the warning
        self._represented_context = self._context(instance)
        return super().get_attribute(instance)

    def to_representation(self, value):
        return decrypt_secret(value, context=getattr(self, "_represented_context", self._context(None)))

    def run_validation(self, data=empty):
        plaintext = super().run_validation(data)
        instance = getattr(self.parent, "instance", None)
        source = self.source
        stored = getattr(instance, source, None) if isinstance(instance, models.Model) and source else None
        return encrypt_if_changed(stored, plaintext, context=self._context(instance))


class ChoiceField(serializers.Field):
    def __init__(self, choices, **kwargs):
        """init."""
        self._choices = OrderedDict(choices)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        return self._choices[obj]

    def to_internal_value(self, data):
        for i in self._choices:
            if self._choices[i] == data:
                return i
        raise serializers.ValidationError(f"Could not find value. Acceptable values are {list(self._choices.values())}.")
