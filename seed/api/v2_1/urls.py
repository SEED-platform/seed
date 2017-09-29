# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from rest_framework import routers

from seed.api.v2_1.views import PropertyViewSetV21

router = routers.DefaultRouter()
router.register(r'properties', PropertyViewSetV21, base_name="properties")

urlpatterns = [
    url(r'^', include(router.urls)),
]
