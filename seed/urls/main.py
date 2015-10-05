"""
:copyright: (c) 2014 Building Energy Inc
"""
# !/usr/bin/env python
# encoding: utf-8
"""
urls/urls.py

Copyright (c) 2013 Building Energy. All rights reserved.
"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.views.main',
    # template routes
    url(r'^$', 'home', name='home'),

    # ajax routes
    url(r'^create_pm_mapping/$', 'create_pm_mapping', name='create_pm_mapping'),

    url(
        r'^get_total_number_of_buildings_for_user/$',
        'get_total_number_of_buildings_for_user',
        name='get_total_number_of_buildings_for_user'
    ),
    url(r'^get_building/$', 'get_building', name='get_building'),
    url(
        r'^get_datasets_count/$',
        'get_datasets_count',
        name='get_datasets_count'
    ),
    url(r'^search_buildings/$', 'search_buildings', name='search_buildings'),
    url(
        r'^search_building_snapshots/$',
        'search_building_snapshots',
        name='search_building_snapshots'
    ),
    url(
        r'^get_default_columns/$',
        'get_default_columns',
        name='get_default_columns'
    ),
    url(
        r'^set_default_columns/$',
        'set_default_columns',
        name='set_default_columns'
    ),
    url(r'^get_columns/$', 'get_columns', name='get_columns'),
    url(r'^save_match/$', 'save_match', name='save_match'),
    url(r'^get_match_tree/$', 'get_match_tree', name='get_match_tree'),
    url(r'^get_coparents/$', 'get_coparents', name='get_coparents'),
    url(r'^save_raw_data/$', 'save_raw_data', name='save_raw_data'),
    url(
        r'^get_PM_filter_by_counts/$',
        'get_PM_filter_by_counts',
        name='get_PM_filter_by_counts'
    ),
    url(r'^delete_duplicates_from_import_file/$', 'delete_duplicates_from_import_file', name='delete_duplicates_from_import_file'),
    url(r'^create_dataset/$', 'create_dataset', name='create_dataset'),
    url(r'^get_datasets/$', 'get_datasets', name='get_datasets'),
    url(r'^get_dataset/$', 'get_dataset', name='get_dataset'),
    url(r'^get_import_file/$', 'get_import_file', name='get_import_file'),
    url(r'^delete_file/$', 'delete_file', name='delete_file'),
    url(r'^delete_dataset/$', 'delete_dataset', name='delete_dataset'),
    url(r'^update_dataset/$', 'update_dataset', name='update_dataset'),
    url(r'^update_building/$', 'update_building', name='update_building'),
    
    #DMcQ: Test for building reports    
    url(r'^get_building_summary_report_data/$', 'get_building_summary_report_data', name='get_building_summary_report_data'),
    url(r'^get_building_report_data/$', 'get_building_report_data', name='get_building_report_data'),
    url(r'^get_aggregated_building_report_data/$', 'get_aggregated_building_report_data', name='get_aggregated_building_report_data'),


    # New MCM endpoints
    url(
        r'^get_column_mapping_suggestions/$',
        'get_column_mapping_suggestions',
        name='get_column_mapping_suggestions'
    ),
    url(
        r'^get_raw_column_names/$',
        'get_raw_column_names',
        name='get_raw_column_names'
    ),
    url(
        r'^get_first_five_rows/$',
        'get_first_five_rows',
        name='get_first_five_rows'
    ),
    url(
        r'^save_column_mappings/$',
        'save_column_mappings',
        name='save_column_mappings'
    ),
    url(r'^start_mapping/$', 'start_mapping', name='start_mapping'),
    url(r'^remap_buildings/$', 'remap_buildings', name='remap_buildings'),
    url(
        r'^start_system_matching/$',
        'start_system_matching',
        name='start_system_matching'
    ),
    url(
        r'^public_search/$',
        'public_search',
        name='public_search'
    ),
    url(r'^progress/$', 'progress', name='progress'),

    # exporter routes
    url(r'^export_buildings/$', 'export_buildings', name='export_buildings'),
    url(
        r'^export_buildings/progress/$',
        'export_buildings_progress',
        name='export_buildings_progress'
    ),
    url(
        r'^export_buildings/download/$',
        'export_buildings_download',
        name='export_buildings_download'
    ),

    # test urls
    url(r'^angular_js_tests/$', 'angular_js_tests', name='angular_js_tests'),

    # org
    url(
        r'^delete_organization_buildings/$',
        'delete_organization_buildings',
        name='delete_organization_buildings'
    ),

    # delete
    url(
        r'^delete_buildings/$',
        'delete_buildings',
        name='delete_buildings'
    ),
)
