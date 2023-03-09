# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from django.conf.urls import re_path

from seed.views.main import home

urlpatterns = [
    re_path(r'^$', home, name='home'),
]
