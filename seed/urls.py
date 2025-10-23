"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import path

from seed.views.main import home

urlpatterns = [
    path("", home, name="home"),
]
