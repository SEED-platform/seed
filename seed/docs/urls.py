# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import re_path

from seed.docs.views import (
    faq_page
)

urlpatterns = [
    re_path(r'^$', faq_page, name='documentation'),
]
