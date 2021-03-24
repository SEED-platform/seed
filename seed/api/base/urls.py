# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from django.conf import settings

from seed.api.v1.urls import urlpatterns as apiv1
from seed.api.v2.urls import urlpatterns as apiv2
from seed.api.v2_1.urls import urlpatterns as apiv2_1
from seed.api.v3.urls import urlpatterns as apiv3

urlpatterns = []

if settings.INCLUDE_SEED_V2_APIS:
    urlpatterns = [
        # add flat urls namespace for non-conforming endpoints, ugh
        url(r'^v1/', include((apiv1, 'seed'), namespace='v1')),
        url(r'^v2/', include((apiv2, 'seed'), namespace='v2')),
        url(r'^v2.1/', include((apiv2_1, 'seed'), namespace='v2.1')),
    ]

urlpatterns += [
    url(r'^v3/', include((apiv3, 'seed'), namespace='v3')),
]
