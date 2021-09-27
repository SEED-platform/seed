# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from seed.landing.models import SEEDUser


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        help_text=_("ex: joe@company.com"),
        widget=forms.TextInput(
            attrs={'class': 'field', 'placeholder': _('Email Address')}
        )
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={'class': 'field', 'placeholder': _('Password'), 'autocomplete': 'off'}
        ),
        required=True
    )


class CustomCreateUserForm(UserCreationForm):
    class Meta:
        model = SEEDUser
        fields = ['username']
        widgets = {
            'username': forms.fields.EmailInput(attrs={'placeholder': 'Email Address'})
        }

    def __init__(self, *args, **kwargs):
        super(CustomCreateUserForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'field', 'placeholder': 'Password'})
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'field', 'placeholder': 'Confirm Password'})
