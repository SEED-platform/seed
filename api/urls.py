# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include

from seed.views.datasets import DatasetViewSet
from seed.views.organizations import OrganizationViewSet
from seed.views.main import DataFileViewSet
from api.views import TestReverseViewSet
from rest_framework import routers

api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'datasets', DatasetViewSet, base_name="datasets")
api_v2_router.register(r'organizations', OrganizationViewSet, base_name="organizations")
api_v2_router.register(r'data_files', DataFileViewSet, base_name="data_files")
api_v2_router.register(r'reverse_test', TestReverseViewSet, base_name="reverse_test")

urlpatterns = [
    # v2 api
    url(r'^', include(api_v2_router.urls)),  # , namespace='ap')),
    # swagger urls
    url(
        r'^swagger/',
        include('rest_framework_swagger.urls'),
        name='swagger'
    ),
]
