# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm

from passwords.fields import PasswordField


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        help_text=_("ex: joe@company.com"),
        widget=forms.TextInput(
            attrs={'class': 'field', 'placeholder': 'Email Address'}
        )
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={'class': 'field', 'placeholder': 'Password'}
        ),
        required=True
    )


class SetStrongPasswordForm(SetPasswordForm):
    """
    The Django SetPasswordForm with django-passwords PasswordField
    """
    new_password2 = PasswordField(
        label=_("New password confirmation"),
        widget=forms.PasswordInput
    )
