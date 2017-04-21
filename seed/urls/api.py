# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include

urlpatterns = [
    # swagger urls
    url(
        r'^swagger/',
        include('rest_framework_swagger.urls'),
        name='swagger'
    ),
]
