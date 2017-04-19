# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url
from django.contrib.auth.views import (
    logout, password_change, password_change_done
)

from seed.landing.views import (
    landing_page, login_view, password_reset, password_reset_done,
    password_reset_confirm, password_reset_complete, signup
)

urlpatterns = [
    url(r'^$', landing_page, name='landing_page'),
    url(r'^accounts/login/$', login_view, name='login'),
    url(
        r'^accounts/logout/$',
        logout,
        {'next_page': '/?logout'},
        name='logout'
    ),
    url(r'^accounts/password/reset/$', password_reset, name='password_reset'),
    url(r'^accounts/password/reset/done/$', password_reset_done, name='password_reset_done'),
    url(
        (
            r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/'
            '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'
        ),
        password_reset_confirm,
        name='password_reset_confirm'
    ),
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
        password_change,
        {'template_name': 'landing/password_change_form.html'},
        name="password_change"
    ),
    url(
        r'^password_change/done/$',
        password_change_done,
        {'template_name': 'landing/password_change_done.html'}
    ),
]
