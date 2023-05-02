# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf import settings
from django.conf.urls import include, re_path

from seed.api.v1.urls import urlpatterns as apiv1
from seed.api.v2.urls import urlpatterns as apiv2
from seed.api.v2_1.urls import urlpatterns as apiv2_1
from seed.api.v3.urls import urlpatterns as apiv3

urlpatterns = []

if settings.INCLUDE_SEED_V2_APIS:
    urlpatterns = [
        # add flat urls namespace for non-conforming endpoints, ugh
        re_path(r'^v1/', include((apiv1, 'seed'), namespace='v1')),
        re_path(r'^v2/', include((apiv2, 'seed'), namespace='v2')),
        re_path(r'^v2.1/', include((apiv2_1, 'seed'), namespace='v2.1')),
    ]

urlpatterns += [
    re_path(r'^v3/', include((apiv3, 'seed'), namespace='v3')),
]
