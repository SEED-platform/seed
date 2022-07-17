"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordBaseCharacterQuantityValidator(object):
    TYPE = ''
    RE = re.compile(r'')

    def __init__(self, quantity=1):
        self.quantity = quantity

    def validate(self, password, user=None):
        if len(self.RE.findall(password)) < self.quantity:
            raise ValidationError(
                _("This password must contain at least %(quantity)d %(type)s characters."),
                code='password_not_enough_%s' % self.TYPE,
                params={'quantity': self.quantity, 'type': self.TYPE},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least %(quantity)d %(type)s characters."
            % {'quantity': self.quantity, 'type': self.TYPE}
        )


class PasswordUppercaseCharacterValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = 'uppercase'
    RE = re.compile(r'[A-Z]')


class PasswordLowercaseCharacterValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = 'lowercase'
    RE = re.compile(r'[a-z]')


class PasswordDigitValidator(PasswordBaseCharacterQuantityValidator):
    TYPE = 'numeric'
    RE = re.compile(r'[0-9]')
