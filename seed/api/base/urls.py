# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url, include

from seed.api.v1.urls import urlpatterns as apiv1
from seed.api.v2.urls import urlpatterns as apiv2
from seed.api.v2_1.urls import urlpatterns as apiv2_1

urlpatterns = [
    url(r'^v1/', include(apiv1, namespace="v1")),
    url(r'^v2/', include(apiv2, namespace="v2")),
    url(r'^v2\.1/', include(apiv2_1, namespace="v2.1")),
]
