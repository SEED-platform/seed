# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf.urls import re_path

from seed.docs.views import faq_page

urlpatterns = [
    re_path(r'^$', faq_page, name='documentation'),
]
