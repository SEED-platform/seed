# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.conf.urls import url

from seed.views.properties import (get_properties, get_property_columns,
                                   get_taxlot, get_taxlots, get_taxlot_columns,
                                   get_cycles, Property)

urlpatterns = [
    url(r'^properties/$', get_properties, name='properties'),
    url(r'^lots/$', get_taxlots, name='lots'),
    url(r'^lot/(?P<taxlot_pk>\d+)/$', get_taxlot, name='lot-detail'),
    url(r'^cycles/$', get_cycles, name='cycles'),
    url(r'^property-columns/$', get_property_columns,
        name='property-columns'),
    url(r'^taxlot-columns/$', get_taxlot_columns, name='taxlot-columns'),
    url(r'^property/(?P<property_pk>\d+)/$',
        Property.as_view({'get': 'get_property'}), name='property-details'),
    url(r'^update-property/(?P<property_pk>\d+)/$',
        Property.as_view({'put': 'put'}), name='update-property-details'),
]
