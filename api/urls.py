# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from rest_framework import routers

from api.views import test_view_with_arg, TestReverseViewSet
from seed.views.datasets import DatasetViewSet
from seed.views.main import DataFileViewSet, version, progress
from seed.views.organizations import OrganizationViewSet
from seed.views.projects import ProjectViewSet
from seed.views.users import UserViewSet
from seed.views.api import get_api_schema
from seed.data_importer.views import (
    handle_s3_upload_complete, get_upload_details, sign_policy_document,
    local_uploader
)
from seed.views.import_files import ImportFileViewSet

api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'datasets', DatasetViewSet, base_name="datasets")
api_v2_router.register(r'organizations', OrganizationViewSet, base_name="organizations")
api_v2_router.register(r'data_files', DataFileViewSet, base_name="data_files")
api_v2_router.register(r'projects', ProjectViewSet, base_name="projects")
api_v2_router.register(r'users', UserViewSet, base_name="users")
api_v2_router.register(r'import_files', ImportFileViewSet, base_name="import_files")
api_v2_router.register(r'reverse_and_test', TestReverseViewSet, base_name="reverse_and_test")

urlpatterns = [
    # v2 api
    url(r'^', include(api_v2_router.urls)),
    # ajax routes
    url(r'^version/$', version, name='version'),
    # data uploader related things
    url(r's3_upload_complete/$', handle_s3_upload_complete, name='s3_upload_complete'),
    url(r'get_upload_details/$', get_upload_details, name='get_upload_details'),
    url(r'sign_policy_document/$', sign_policy_document, name='sign_policy_document'),
    url(r'upload/$', local_uploader, name='local_uploader'),
    # api schema
    url(
        r'^schema/$',
        get_api_schema,
        name='schema'
    ),
    url(
        r'^progress/$',
        progress,
        name='progress'
    ),
    url(
        r'projects/(?P<pk>\w+)/add/$',
        ProjectViewSet.as_view({'put': 'add'}),
        name='projects-add-inventory'
    ),
    url(
        r'projects/(?P<pk>\w+)/remove/$',
        ProjectViewSet.as_view({'put': 'remove'}),
        name='projects-remove-inventory'
    ),
    url(
        r'projects/(?P<pk>\w+)/update/$',
        ProjectViewSet.as_view({'put': 'update_details'}),
        name='projects-update'
    ),
    url(
        r'projects/(?P<pk>\w+)/move/$',
        ProjectViewSet.as_view({'put': 'transfer'}),
        {'action': 'move'},
        name='projects-move'
    ),
    url(
        r'projects/(?P<pk>\w+)/copy/$',
        ProjectViewSet.as_view({'put': 'transfer'}),
        {'action': 'copy'},
        name='projects-copy'
    ),
    url(
        r'^test_view_with_arg/([0-9]{1})/$',
        test_view_with_arg,
        name='testviewarg'
    ),
]
