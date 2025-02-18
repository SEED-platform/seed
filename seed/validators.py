"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordBaseCharacterQuantityValidator:
    TYPE = ""
    RE = re.compile(r"")

    def __init__(self, quantity=1):
        self.quantity = quantity

    def validate(self, password, user=None):
        if len(self.RE.findall(password)) < self.quantity:
            raise ValidationError(
                _("This password must contain at least %(quantity)d %(type)s characters."),
                code=f"password_not_enough_{self.TYPE}",
                params={"quantity": self.quantity, "type": self.TYPE},
            )

    def get_help_text(self):
        return _(f"Your password must contain at least {self.quantity:d} {self.TYPE} characters.")


class PasswordUppercaseCharacterValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = "uppercase"
    RE = re.compile(r"[A-Z]")


class PasswordLowercaseCharacterValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = "lowercase"
    RE = re.compile(r"[a-z]")


class PasswordDigitValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = "numeric"
    RE = re.compile(r"[0-9]")
