# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url, include
from rest_framework import routers

from seed.views.main import (
    set_default_columns,
    get_default_building_detail_columns,
    set_default_building_detail_columns,
    public_search,
    delete_organization_inventory,
)

router = routers.DefaultRouter()

urlpatterns = [
    # template routes
    url(r'^', include(router.urls)),
    url(r'^set_default_columns/$', set_default_columns, name='set_default_columns'),
    url(
        r'^get_default_building_detail_columns/$',
        get_default_building_detail_columns,
        name='get_default_building_detail_columns'
    ),
    url(
        r'^set_default_building_detail_columns/$',
        set_default_building_detail_columns,
        name='set_default_building_detail_columns'
    ),
    url(r'^public_search/$', public_search, name='public_search'),
    url(
        r'^delete_organization_inventory/$',
        delete_organization_inventory,
        name='delete_organization_inventory'
    ),
]
