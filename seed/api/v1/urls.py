# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.conf.urls import include, re_path
from rest_framework import routers

from seed.views.main import (
    delete_organization_inventory,
    get_default_building_detail_columns,
    public_search,
    set_default_building_detail_columns,
    set_default_columns
)

router = routers.DefaultRouter()

urlpatterns = [
    # template routes
    re_path(r'^', include(router.urls)),
    re_path(r'^set_default_columns/$', set_default_columns, name='set_default_columns'),
    re_path(
        r'^get_default_building_detail_columns/$',
        get_default_building_detail_columns,
        name='get_default_building_detail_columns'
    ),
    re_path(
        r'^set_default_building_detail_columns/$',
        set_default_building_detail_columns,
        name='set_default_building_detail_columns'
    ),
    re_path(r'^public_search/$', public_search, name='public_search'),
    re_path(
        r'^delete_organization_inventory/$',
        delete_organization_inventory,
        name='delete_organization_inventory'
    ),
]
