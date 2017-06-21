# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from rest_framework import routers

from api.views import test_view_with_arg, TestReverseViewSet
from seed.data_importer.views import ImportFileViewSet
from seed.data_importer.views import (
    handle_s3_upload_complete,
    get_upload_details,
    sign_policy_document,
    LocalUploaderViewSet
)
from seed.views.api import get_api_schema
from seed.views.columns import ColumnViewSet, ColumnMappingViewSet
from seed.views.certification import (
    GreenAssessmentViewSet,
    GreenAssessmentPropertyViewSet,
    GreenAssessmentURLViewSet
)
from seed.views.data_quality import DataQualityViews
from seed.views.cycles import CycleViewSet
from seed.views.datasets import DatasetViewSet
from seed.views.labels import LabelViewSet, UpdateInventoryLabelsAPIView
from seed.views.main import version, progress
from seed.views.organizations import OrganizationViewSet
from seed.views.projects import ProjectViewSet
from seed.views.properties import (PropertyViewSet, PropertyStateViewSet,
                                   PropertyViewViewSet, GBRPropertyViewSet)
from seed.views.taxlots import TaxLotViewSet
from seed.views.users import UserViewSet

api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'columns', ColumnViewSet, base_name="columns")
api_v2_router.register(r'column_mappings', ColumnMappingViewSet, base_name="column_mappings")
api_v2_router.register(r'datasets', DatasetViewSet, base_name="datasets")
api_v2_router.register(r'organizations', OrganizationViewSet, base_name="organizations")
api_v2_router.register(r'green_assessments', GreenAssessmentViewSet, base_name="green_assessments")
api_v2_router.register(r'green_assessment_urls', GreenAssessmentURLViewSet, base_name="green_assessment_urls")
api_v2_router.register(r'green_assessment_properties', GreenAssessmentPropertyViewSet, base_name="green_assessment_properties")
api_v2_router.register(r'projects', ProjectViewSet, base_name="projects")
api_v2_router.register(r'users', UserViewSet, base_name="users")
api_v2_router.register(r'reverse_and_test', TestReverseViewSet, base_name="reverse_and_test")
api_v2_router.register(r'labels', LabelViewSet, base_name="labels")
api_v2_router.register(r'import_files', ImportFileViewSet, base_name="import_files")
api_v2_router.register(r'cycles', CycleViewSet, base_name="cycles")
api_v2_router.register(r'properties', PropertyViewSet, base_name="properties")
api_v2_router.register(r'taxlots', TaxLotViewSet, base_name="taxlots")
api_v2_router.register(r'reverse_and_test', TestReverseViewSet, base_name="reverse_and_test")
api_v2_router.register(r'upload', LocalUploaderViewSet, base_name='local_uploader')
api_v2_router.register(r'data_quality_checks', DataQualityViews, base_name='data_quality_checks')
api_v2_router.register(r'gbr_properties', GBRPropertyViewSet, base_name="properties")
api_v2_router.register(r'property_states', PropertyStateViewSet, base_name="property_states")
api_v2_router.register(r'property_views', PropertyViewViewSet, base_name="property_views")
api_v2_router.register(r'properties', PropertyViewSet, base_name="seed_properties")

urlpatterns = [
    # v2 api
    url(r'^', include(api_v2_router.urls)),
    # ajax routes
    url(r'^version/$', version, name='version'),
    # data uploader related things
    url(r's3_upload_complete/$', handle_s3_upload_complete, name='s3_upload_complete'),
    url(r'get_upload_details/$', get_upload_details, name='get_upload_details'),
    url(r'sign_policy_document/$', sign_policy_document, name='sign_policy_document'),
    # api schema
    url(r'^schema/$', get_api_schema, name='schema'),
    url(r'^progress/$', progress, name='progress'),
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
        r'labels-property/$',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'property'},
        name="property-labels",
    ),
    url(
        r'labels-taxlot/$',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'taxlot'},
        name="taxlot-labels",
    ),
    url(
        r'^test_view_with_arg/([0-9]{1})/$',
        test_view_with_arg,
        name='testviewarg'
    ),
    # url(
    #     r'^property/',
    #     UpdateInventoryLabelsAPIView.as_view(),
    #     {'inventory_type': 'property'},
    #     name="property_labels",
    # ),
    # url(
    #     r'^taxlot/$',
    #     UpdateInventoryLabelsAPIView.as_view(),
    #     {'inventory_type': 'taxlot'},
    #     name="taxlot_labels",
    # ),
]
