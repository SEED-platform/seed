# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url, include
from rest_framework import routers

from seed.api.v1.views import ColumnViewSetV1
from seed.views.main import (
    search_buildings,
    get_default_columns,
    set_default_columns,
    get_default_building_detail_columns,
    set_default_building_detail_columns,
    public_search,
    export_buildings_download,
    delete_organization_inventory,
)

router = routers.DefaultRouter()
router.register(r'columns', ColumnViewSetV1, base_name="columns")

urlpatterns = [
    # template routes
    url(r'^', include(router.urls)),

    url(r'^search_buildings/$', search_buildings, name='search_buildings'),
    url(r'^get_default_columns/$', get_default_columns, name='get_default_columns'),
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
    # url(r'^get_columns/$', get_columns, name='get_columns'),
    # url(r'^delete_file/$', delete_file, name='delete_file'),
    url(r'^public_search/$', public_search, name='public_search'),
    url(
        r'^export_buildings/download/$',
        export_buildings_download,
        name='export_buildings_download'
    ),
    url(
        r'^delete_organization_inventory/$',
        delete_organization_inventory,
        name='delete_organization_inventory'
    ),
]
