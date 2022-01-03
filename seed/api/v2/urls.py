# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from rest_framework import routers

from seed.api.base.views import test_view_with_arg, TestReverseViewSet
from seed.api.v2.views import ProgressViewSetV2
from seed.data_importer.views import ImportFileViewSet
from seed.data_importer.views import (
    get_upload_details,
    LocalUploaderViewSet
)
from seed.views.api import get_api_schema
from seed.views.building_file import BuildingFileViewSet
from seed.views.certification import (
    GreenAssessmentViewSet,
    GreenAssessmentPropertyViewSet,
    GreenAssessmentURLViewSet
)
from seed.views.columns import ColumnViewSet
from seed.views.column_mappings import ColumnMappingViewSet
from seed.views.column_list_settings import ColumnListingViewSet
from seed.views.column_mapping_presets import ColumnMappingPresetViewSet
from seed.views.cycles import CycleViewSet
from seed.views.data_quality import DataQualityViews
from seed.views.datasets import DatasetViewSet
from seed.views.geocode import GeocodeViews
from seed.views.labels import LabelViewSet, UpdateInventoryLabelsAPIView
from seed.views.main import version
from seed.views.measures import MeasureViewSet
from seed.views.meters import MeterViewSet
from seed.views.organizations import OrganizationViewSet
from seed.views.projects import ProjectViewSet
from seed.views.properties import (PropertyViewSet, PropertyStateViewSet,
                                   PropertyViewViewSet, GBRPropertyViewSet)
from seed.views.reports import Report
from seed.views.taxlots import TaxLotViewSet
from seed.views.ubid import UbidViews
from seed.views.users import UserViewSet

api_v2_router = routers.DefaultRouter()
api_v2_router.register(r'building_file', BuildingFileViewSet, basename='building_file')
api_v2_router.register(r'columns', ColumnViewSet, basename="columns")
api_v2_router.register(r'column_mappings', ColumnMappingViewSet, basename="column_mappings")
api_v2_router.register(r'column_mapping_presets', ColumnMappingPresetViewSet, basename="column_mapping_presets")
api_v2_router.register(r'column_list_settings', ColumnListingViewSet, basename="column_list_settings")
api_v2_router.register(r'cycles', CycleViewSet, basename="cycles")
api_v2_router.register(r'data_quality_checks', DataQualityViews, basename='data_quality_checks')
api_v2_router.register(r'datasets', DatasetViewSet, basename="datasets")
api_v2_router.register(r'import_files', ImportFileViewSet, basename="import_files")
api_v2_router.register(r'gbr_properties', GBRPropertyViewSet, basename="properties")
api_v2_router.register(r'geocode', GeocodeViews, basename="geocode")
api_v2_router.register(r'green_assessment_urls', GreenAssessmentURLViewSet, basename="green_assessment_urls")
api_v2_router.register(r'green_assessment_properties', GreenAssessmentPropertyViewSet,
                       basename="green_assessment_properties")
api_v2_router.register(r'green_assessments', GreenAssessmentViewSet, basename="green_assessments")
api_v2_router.register(r'labels', LabelViewSet, basename="labels")
api_v2_router.register(r'measures', MeasureViewSet, basename='measures')
api_v2_router.register(r'meters', MeterViewSet, basename='meters')
api_v2_router.register(r'organizations', OrganizationViewSet, basename="organizations")
api_v2_router.register(r'progress', ProgressViewSetV2, basename="progress")
api_v2_router.register(r'projects', ProjectViewSet, basename="projects")
api_v2_router.register(r'properties', PropertyViewSet, basename="properties")
api_v2_router.register(r'property_states', PropertyStateViewSet, basename="property_states")
api_v2_router.register(r'property_views', PropertyViewViewSet, basename="property_views")
api_v2_router.register(r'reverse_and_test', TestReverseViewSet, basename="reverse_and_test")
api_v2_router.register(r'taxlots', TaxLotViewSet, basename="taxlots")
api_v2_router.register(r'ubid', UbidViews, basename="ubid")
api_v2_router.register(r'upload', LocalUploaderViewSet, basename='local_uploader')
api_v2_router.register(r'users', UserViewSet, basename="users")

urlpatterns = [
    # v2 api
    url(r'^', include(api_v2_router.urls)),
    # ajax routes
    url(r'^version/$', version, name='version'),
    # data uploader related things
    url(r'get_upload_details/$', get_upload_details, name='get_upload_details'),
    url(r'^schema/$', get_api_schema, name='schema'),
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
        ProjectViewSet.as_view({'put': 'move'}),
        name='projects-move'
    ),
    url(
        r'projects/(?P<pk>\w+)/copy/$',
        ProjectViewSet.as_view({'put': 'copy'}),
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
    url(
        r'^export_reports_data/$',
        Report.as_view({'get': 'export_reports_data'}),
        name='export_reports_data'
    ),
    url(
        r'^get_property_report_data/$',
        Report.as_view({'get': 'get_property_report_data'}),
        name='property_report_data'
    ),
    url(
        r'^get_aggregated_property_report_data/$',
        Report.as_view({'get': 'get_aggregated_property_report_data'}),
        name='aggregated_property_report_data'
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
