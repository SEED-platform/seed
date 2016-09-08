# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include

from seed.views.datasets import DatasetViewSet
from seed.views.main import DataFileViewSet
from seed.views.projects import ProjectsViewSet
from seed.views.organizations import OrganizationViewSet
from seed.views.accounts import UserViewSet
from seed.views.labels import LabelViewSet
from api.views import TestReverseViewSet, test_view_with_arg
from rest_framework import routers


from seed.views.properties import (get_properties, get_property_columns,
                                   get_taxlots, get_taxlot_columns,
                                   get_cycles, Property, TaxLot)

from seed.views.reports import Report


api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'datasets', DatasetViewSet, base_name="datasets")
api_v2_router.register(r'organizations', OrganizationViewSet, base_name="organizations")
api_v2_router.register(r'data_files', DataFileViewSet, base_name="data_files")
api_v2_router.register(r'projects', ProjectsViewSet, base_name="projects")
api_v2_router.register(r'users', UserViewSet, base_name="users")
# api_v2_router.register(r'labels', LabelViewSet, base_name="labels")
# api_v2_router.register(r'reverse_test', TestReverseViewSet, base_name="reverse_test")

urlpatterns = [
    # v2 api
    url(r'^', include(api_v2_router.urls)),

    url(
        r'^test_view_with_arg/([0-9]{1})/$',
        test_view_with_arg,
        name='testviewarg'
    ),

    url(r'^properties/$', get_properties, name='properties'),
    url(r'^taxlots/$', get_taxlots, name='taxlots'),
    url(r'^cycles/$', get_cycles, name='cycles'),
    url(r'^property-columns/$', get_property_columns, name='property-columns'),
    url(r'^taxlot-columns/$', get_taxlot_columns, name='taxlot-columns'),
    url(r'^properties/(?P<property_pk>\d+)/cycles/(?P<cycle_pk>\d+)/$',
        Property.as_view({'get': 'get_property'}), name='property-details'),
    url(r'^properties/(?P<property_pk>\d+)/cycles/(?P<cycle_pk>\d+)/$',
        Property.as_view({'put': 'put'}), name='update-property-details'),
    url(r'^taxlots/(?P<taxlot_pk>\d+)/cycles/(?P<cycle_pk>\d+)/$',
        TaxLot.as_view({'get': 'get_taxlot'}), name='taxlot-details'),
    url(r'^taxlots/(?P<taxlots_pk>\d+)/cycles/(?P<cycle_pk>\d+)/$',
        TaxLot.as_view({'put': 'put'}), name='update-taxlot-details'),
    # url(r'^get_property_report_data/$',
    #    Report.as_view({'get': 'get_property_report_data'}),
    #    name='property_report_data'),
    # url(r'^get_aggregated_property_report_data/$',
    #    Report.as_view({'get': 'get_aggregated_property_report_data'}),
    #    name='aggregated_property_report_data'),
]
