# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url

from seed.views.reports import Report

urlpatterns = [
    url(r'^get_property_report_data/$', Report.as_view({'get': 'get_property_report_data'}),
        name='property_report_data'),
    url(r'^get_aggregated_property_report_data/$', Report.as_view({'get': 'get_aggregated_property_report_data'}),
        name='aggregated_property_report_data'),
]
