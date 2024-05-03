# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.contrib.auth.views import LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.urls import re_path

from seed.landing.views import (
    account_activation_sent,
    activate,
    create_account,
    landing_page,
    password_reset,
    password_reset_complete,
    password_reset_done,
    signup,
)

urlpatterns = [
    re_path(r"^$", landing_page, name="landing_page"),
    re_path(r"^accounts/login/$", landing_page, name="login"),
    re_path(r"^accounts/logout/$", LogoutView.as_view(next_page="/"), name="logout"),
    # re_path(r"^accounts/logout/$", logout_then_login, name="logout"),
    re_path(r"^accounts/password/reset/$", password_reset, name="password_reset"),
    re_path(r"^accounts/password/reset/done/$", password_reset_done, name="password_reset_done"),
    re_path(
        r"^accounts/password/reset/complete/$",
        password_reset_complete,
        name="password_reset_complete",
    ),
    re_path((r"^accounts/setup/(?P<uidb64>[0-9A-Za-z_\-]+)/" "(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$"), signup, name="signup"),
    re_path(
        r"^password_change/$", PasswordChangeView.as_view(), {"template_name": "landing/password_change_form.html"}, name="password_change"
    ),
    re_path(r"^password_change/done/$", PasswordChangeDoneView.as_view(), {"template_name": "landing/password_change_done.html"}),
]

if settings.INCLUDE_ACCT_REG:
    urlpatterns += [
        re_path(r"^accounts/create/$", create_account, name="create_account"),
        re_path(r"^account_activation_sent/$", account_activation_sent, name="account_activation_sent"),
        re_path(r"^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$", activate, name="activate"),
    ]
