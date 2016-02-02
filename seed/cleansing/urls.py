# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'seed.cleansing.views',
    url(r'results/', 'get_cleansing_results', name='get_cleansing_results'),
    url(r'progress/', 'get_progress', name='get_progress'),
    url(r'download/', 'get_csv', name='get_csv'),
)
