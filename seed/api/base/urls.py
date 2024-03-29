# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import include, re_path

from seed.api.v3.urls import urlpatterns as api_v3
from seed.views.main import error410

deprecated_apis = [
    re_path(r'^v1/', error410, name='v1'),
    re_path(r'^v2/', error410, name='v2'),
    re_path(r'^v2\.1/', error410, name='v2.1'),
]

urlpatterns = deprecated_apis + [
    re_path(r'^v3/', include((api_v3, 'seed'), namespace='v3')),
]
