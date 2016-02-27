# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'seed.views.projects',
    url(
        r'^add_buildings_to_project/$', 'add_buildings_to_project',
        name='add_buildings_to_project',
    ),
    url(r'^create_project/$', 'create_project', name='create_project'),
    url(r'^delete_project/$', 'delete_project', name='delete_project'),
    url(
        r'^get_adding_buildings_to_project_status_percentage/$',
        'get_adding_buildings_to_project_status_percentage',
        name='get_adding_buildings_to_project_status_percentage'
    ),
    url(r'^get_project/$', 'get_project', name='get_project'),
    url(r'^get_projects/$', 'get_projects', name='get_projects'),
    url(r'^get_projects_count/$', 'get_projects_count', name='get_projects_count'),
    url(r'^move_buildings/$', 'move_buildings', name='move_buildings'),
    url(
        r'^remove_buildings_from_project/$', 'remove_buildings_from_project',
        name='remove_buildings_from_project',
    ),
    url(r'^update_project/$', 'update_project', name='update_project'),
    url(r'^update_project_building/$', 'update_project_building', name='update_project_building'),
)
