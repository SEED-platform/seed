# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.audit_logs.views',
    url(r'^get_building_logs/$', 'get_building_logs', name='get_building_logs'),
    url(r'^create_note/$', 'create_note', name='create_note'),
    url(r'^update_note/$', 'update_note', name='update_note'),
)
