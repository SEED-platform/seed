"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import path

from seed.docs.views import faq_page

urlpatterns = [
    path("", faq_page, name="documentation"),
]
