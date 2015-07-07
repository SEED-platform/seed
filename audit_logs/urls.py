"""
:copyright: (c) 2014 Building Energy Inc
"""
#!/usr/bin/env python
# encoding: utf-8
"""
urls/urls.py

Copyright (c) 2013 Building Energy. All rights reserved.
"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'audit_logs.views',
    url(
        r'^get_building_logs/$',
        'get_building_logs',
        name='get_building_logs'
    ),
    url(
        r'^create_note/$',
        'create_note',
        name='create_note'
    ),
    url(
        r'^update_note/$',
        'update_note',
        name='update_note'
    ),
)
