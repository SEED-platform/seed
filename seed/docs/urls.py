# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import re_path

from seed.docs.views import faq_page

urlpatterns = [
    re_path(r"^$", faq_page, name="documentation"),
]
