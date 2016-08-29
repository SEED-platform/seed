# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url, include

from seed.views.main import (
    home, version, create_pm_mapping, get_total_number_of_buildings_for_user,
    get_building, get_datasets_count, search_buildings,
    search_building_snapshots,
    get_default_columns, set_default_columns,
    get_default_building_detail_columns,
    set_default_building_detail_columns, get_columns, save_match,
    get_match_tree,
    get_coparents, save_raw_data, get_PM_filter_by_counts,
    delete_duplicates_from_import_file,
    create_dataset, get_datasets, get_dataset, get_import_file, delete_file,
    delete_dataset,
    update_dataset, update_building, get_building_summary_report_data,
    get_building_report_data,
    get_aggregated_building_report_data, get_column_mapping_suggestions,
    get_raw_column_names,
    get_first_five_rows, save_column_mappings, start_mapping, remap_buildings,
    start_system_matching, public_search, progress, export_buildings,
    export_buildings_progress,
    export_buildings_download, angular_js_tests, delete_organization_buildings,
    delete_buildings, delete_organization
)

from seed.views.datasets import DatasetViewSet
from seed.views.organizations import OrganizationViewSet
from rest_framework import routers
api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'datasets', DatasetViewSet, base_name="datasets")
api_v2_router.register(r'organizations', OrganizationViewSet, base_name="organizations")

# prefix, to revert back to original endpoints, leave this blank
apiv1 = r''  # r'api/v1/'

urlpatterns = [
    # template routes
    url(r'^$', home, name='home'),

    # ajax routes
    url(r'^' + apiv1 + r'version/$', version, name='version'),

    url(r'^' + apiv1 + r'create_pm_mapping/$', create_pm_mapping, name='create_pm_mapping'),

    url(
        r'^' + apiv1 + r'get_total_number_of_buildings_for_user/$',
        get_total_number_of_buildings_for_user,
        name='get_total_number_of_buildings_for_user'
    ),
    url(r'^' + apiv1 + r'get_building/$', get_building, name='get_building'),
    url(
        r'^' + apiv1 + r'get_datasets_count/$',
        get_datasets_count,
        name='get_datasets_count'
    ),
    url(r'^' + apiv1 + r'search_buildings/$', search_buildings, name='search_buildings'),
    url(
        r'^' + apiv1 + r'search_building_snapshots/$',
        search_building_snapshots,
        name='search_building_snapshots'
    ),
    url(
        r'^' + apiv1 + r'get_default_columns/$',
        get_default_columns,
        name='get_default_columns'
    ),
    url(
        r'^' + apiv1 + r'set_default_columns/$',
        set_default_columns,
        name='set_default_columns'
    ),
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
    url(r'^' + apiv1 + r'save_match/$', save_match, name='save_match'),
    url(r'^' + apiv1 + r'get_match_tree/$', get_match_tree, name='get_match_tree'),
    url(r'^' + apiv1 + r'get_coparents/$', get_coparents, name='get_coparents'),
    url(r'^' + apiv1 + r'save_raw_data/$', save_raw_data, name='save_raw_data'),
    url(
        r'^' + apiv1 + r'get_PM_filter_by_counts/$',
        get_PM_filter_by_counts,
        name='get_PM_filter_by_counts'
    ),
    url(
        r'^' + apiv1 + r'delete_duplicates_from_import_file/$',
        delete_duplicates_from_import_file,
        name='delete_duplicates_from_import_file',
    ),
    url(r'^' + apiv1 + r'create_dataset/$', create_dataset, name='create_dataset'),
    url(r'^' + apiv1 + r'get_datasets/$', get_datasets, name='get_datasets'),
    url(r'^' + apiv1 + r'get_dataset/$', get_dataset, name='get_dataset'),
    url(r'^' + apiv1 + r'get_import_file/$', get_import_file, name='get_import_file'),
    url(r'^' + apiv1 + r'delete_file/$', delete_file, name='delete_file'),
    url(r'^' + apiv1 + r'delete_dataset/$', delete_dataset, name='delete_dataset'),
    url(r'^' + apiv1 + r'update_dataset/$', update_dataset, name='update_dataset'),
    url(r'^' + apiv1 + r'update_building/$', update_building, name='update_building'),

    # Building reports
    url(
        r'^' + apiv1 + r'get_building_summary_report_data/$',
        get_building_summary_report_data,
        name='get_building_summary_report_data',
    ),
    url(
        r'^' + apiv1 + r'get_building_report_data/$',
        get_building_report_data,
        name='get_building_report_data',
    ),
    url(
        r'^' + apiv1 + r'get_aggregated_building_report_data/$',
        get_aggregated_building_report_data,
        name='get_aggregated_building_report_data',
    ),

    # New MCM endpoints
    url(
        r'^' + apiv1 + r'get_column_mapping_suggestions/$',
        get_column_mapping_suggestions,
        name='get_column_mapping_suggestions'
    ),
    url(
        r'^' + apiv1 + r'get_raw_column_names/$',
        get_raw_column_names,
        name='get_raw_column_names'
    ),
    url(
        r'^' + apiv1 + r'get_first_five_rows/$',
        get_first_five_rows,
        name='get_first_five_rows'
    ),
    url(
        r'^' + apiv1 + r'save_column_mappings/$',
        save_column_mappings,
        name='save_column_mappings'
    ),
    url(r'^' + apiv1 + r'start_mapping/$', start_mapping, name='start_mapping'),
    url(r'^' + apiv1 + r'remap_buildings/$', remap_buildings, name='remap_buildings'),
    url(
        r'^' + apiv1 + r'start_system_matching/$',
        start_system_matching,
        name='start_system_matching'
    ),
    url(
        r'^' + apiv1 + r'public_search/$',
        public_search,
        name='public_search'
    ),
    url(r'^' + apiv1 + r'progress/$', progress, name='progress'),

    # exporter routes
    url(r'^' + apiv1 + r'export_buildings/$', export_buildings, name='export_buildings'),
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

    # delete
    url(
        r'^' + apiv1 + r'delete_buildings/$',
        delete_buildings,
        name='delete_buildings'
    ),

    # delete org
    url(
        r'^' + apiv1 + r'delete_organization/$',
        delete_organization,
        name='delete_organization'
    ),
    # swagger urls
    url(
        r'^api-docs/',
        include('rest_framework_swagger.urls'),
        name='swagger'
    ),

    # v2 api
    url(r'^api/v2/', include(api_v2_router.urls), name='apiv2'),

]
