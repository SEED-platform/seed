# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url
from django.contrib.auth.views import (
    logout_then_login, PasswordChangeView, PasswordChangeDoneView
)

from seed.landing.views import (
    landing_page, login_view, password_reset, password_reset_done,
    password_reset_complete, signup
)

urlpatterns = [
    url(r'^$', landing_page, name='landing_page'),
    url(r'^accounts/login/$', login_view, name='login'),
    url(
        r'^accounts/logout/$',
        logout_then_login,
        name='logout'
    ),
    url(r'^accounts/password/reset/$', password_reset, name='password_reset'),
    url(r'^accounts/password/reset/done/$', password_reset_done, name='password_reset_done'),
    url(
        r'^accounts/password/reset/complete/$',
        password_reset_complete,
        name='password_reset_complete',
    ),
    url(
        (
            r'^accounts/setup/(?P<uidb64>[0-9A-Za-z_\-]+)/'
            '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'
        ),
        signup,
        name='signup'
    ),
    url(
        r'^password_change/$',
        PasswordChangeView.as_view(),
        {'template_name': 'landing/password_change_form.html'},
        name="password_change"
    ),
    url(
        r'^password_change/done/$',
        PasswordChangeDoneView.as_view(),
        {'template_name': 'landing/password_change_done.html'}
    ),
]
