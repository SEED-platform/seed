# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url

from seed.views.main import (
    home,
    search_buildings,
    get_default_columns,
    set_default_columns,
    get_default_building_detail_columns,
    set_default_building_detail_columns,
    get_columns,
    delete_file,
    public_search, export_buildings,
    export_buildings_progress,
    export_buildings_download,
    angular_js_tests,
    delete_organization_buildings,
    delete_organization_inventory,
    delete_buildings
)

# prefix, to revert back to original endpoints, leave this blank
apiv1 = r''  # r'api/v1/'

urlpatterns = [
    # template routes
    url(r'^$', home, name='home'),
    url(r'^' + apiv1 + r'search_buildings/$', search_buildings, name='search_buildings'),
    url(r'^' + apiv1 + r'get_default_columns/$', get_default_columns, name='get_default_columns'),
    url(r'^' + apiv1 + r'set_default_columns/$', set_default_columns, name='set_default_columns'),
    url(
        r'^' + apiv1 + r'get_default_building_detail_columns/$',
        get_default_building_detail_columns,
        name='get_default_building_detail_columns'
    ),
    url(
        r'^' + apiv1 + r'set_default_building_detail_columns/$',
        set_default_building_detail_columns,
        name='set_default_building_detail_columns'
    ),
    url(r'^' + apiv1 + r'get_columns/$', get_columns, name='get_columns'),
    url(r'^' + apiv1 + r'delete_file/$', delete_file, name='delete_file'),

    # Building reports
    # url(
    #     r'^' + apiv1 + r'get_building_summary_report_data/$',
    #     get_building_summary_report_data,
    #     name='get_building_summary_report_data',
    # ),
    # url(
    #     r'^' + apiv1 + r'get_building_report_data/$',
    #     get_building_report_data,
    #     name='get_building_report_data',
    # ),
    # url(
    #     r'^' + apiv1 + r'get_aggregated_building_report_data/$',
    #     get_aggregated_building_report_data,
    #     name='get_aggregated_building_report_data',
    # ),

    # New MCM endpoints
    url(
        r'^' + apiv1 + r'public_search/$',
        public_search,
        name='public_search'
    ),

    # exporter routes
    url(r'^' + apiv1 + r'export_buildings/$', export_buildings,
        name='export_buildings'),
    url(
        r'^' + apiv1 + r'export_buildings/progress/$',
        export_buildings_progress,
        name='export_buildings_progress'
    ),
    url(
        r'^' + apiv1 + r'export_buildings/download/$',
        export_buildings_download,
        name='export_buildings_download'
    ),

    # test URLs
    url(r'^angular_js_tests/$', angular_js_tests, name='angular_js_tests'),

    # org
    url(
        r'^' + apiv1 + r'delete_organization_buildings/$',
        delete_organization_buildings,
        name='delete_organization_buildings'
    ),
    url(
        r'^' + apiv1 + r'delete_organization_inventory/$',
        delete_organization_inventory,
        name='delete_organization_inventory'
    ),

    # delete
    url(r'^' + apiv1 + r'delete_buildings/$', delete_buildings, name='delete_buildings'),
]
