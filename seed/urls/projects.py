"""
:copyright: (c) 2014 Building Energy Inc
"""
#!/usr/bin/env python
# encoding: utf-8
"""
urls/main.py

Copyright (c) 2013 Building Energy. All rights reserved.
"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.views.projects',
    url(
        r'^add_buildings_to_project/$',
        'add_buildings_to_project',
        name='add_buildings_to_project'
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
    url(
        r'^get_projects_count/$',
        'get_projects_count',
        name='get_projects_count'
    ),
    url(r'^move_buildings/$', 'move_buildings', name='move_buildings'),
    url(
        r'^remove_buildings_from_project/$',
        'remove_buildings_from_project',
        name='remove_buildings_from_project'
    ),
    url(r'^update_project/$', 'update_project', name='update_project'),
    url(
        r'^update_project_building/$',
        'update_project_building',
        name='update_project_building'
    ),
    # labels
    url(r'^get_labels/$', 'get_labels', name='get_labels'),
    url(r'^add_label/$', 'add_label', name='add_label'),
    url(r'^apply_label/$', 'apply_label', name='apply_label'),
    url(r'^delete_label/$', 'delete_label', name='delete_label'),
    url(r'^update_label/$', 'update_label', name='update_label'),
    url(r'^remove_label/$', 'remove_label', name='remove_label'),
)
