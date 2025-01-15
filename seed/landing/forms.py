"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from seed.landing.models import SEEDUser


class CustomCreateUserForm(UserCreationForm):
    class Meta:
        model = SEEDUser
        fields = ["username"]
        widgets = {"username": forms.fields.EmailInput(attrs={"placeholder": "Email Address"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget = forms.PasswordInput(attrs={"class": "field", "placeholder": "Password"})
        self.fields["password2"].widget = forms.PasswordInput(attrs={"class": "field", "placeholder": "Confirm Password"})
