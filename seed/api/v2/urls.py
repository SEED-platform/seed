# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf.urls import include, re_path
from rest_framework import routers

from seed.api.base.views import TestReverseViewSet, test_view_with_arg
from seed.api.v2.views import ProgressViewSetV2
from seed.data_importer.views import (
    ImportFileViewSet,
    LocalUploaderViewSet,
    get_upload_details
)
from seed.views.api import get_api_schema
from seed.views.building_file import BuildingFileViewSet
from seed.views.certification import (
    GreenAssessmentPropertyViewSet,
    GreenAssessmentURLViewSet,
    GreenAssessmentViewSet
)
from seed.views.column_list_settings import ColumnListingViewSet
from seed.views.column_mapping_presets import ColumnMappingPresetViewSet
from seed.views.column_mappings import ColumnMappingViewSet
from seed.views.columns import ColumnViewSet
from seed.views.cycles import CycleViewSet
from seed.views.data_quality import DataQualityViews
from seed.views.datasets import DatasetViewSet
from seed.views.geocode import GeocodeViews
from seed.views.labels import LabelViewSet, UpdateInventoryLabelsAPIView
from seed.views.main import version
from seed.views.measures import MeasureViewSet
from seed.views.meters import MeterViewSetV2
from seed.views.organizations import OrganizationViewSet
from seed.views.properties import (
    GBRPropertyViewSet,
    PropertyStateViewSet,
    PropertyViewSet,
    PropertyViewViewSet
)
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
api_v2_router.register(r'meters', MeterViewSetV2, basename='meters')
api_v2_router.register(r'organizations', OrganizationViewSet, basename="organizations")
api_v2_router.register(r'progress', ProgressViewSetV2, basename="progress")
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
    re_path(r'^', include(api_v2_router.urls)),
    # ajax routes
    re_path(r'^version/$', version, name='version'),
    # data uploader related things
    re_path(r'get_upload_details/$', get_upload_details, name='get_upload_details'),
    re_path(r'^schema/$', get_api_schema, name='schema'),
    re_path(
        r'labels-property/$',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'property'},
        name="property-labels",
    ),
    re_path(
        r'labels-taxlot/$',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'taxlot'},
        name="taxlot-labels",
    ),
    re_path(
        r'^test_view_with_arg/([0-9]{1})/$',
        test_view_with_arg,
        name='testviewarg'
    ),
    re_path(
        r'^export_reports_data/$',
        Report.as_view({'get': 'export_reports_data'}),
        name='export_reports_data'
    ),
    re_path(
        r'^get_property_report_data/$',
        Report.as_view({'get': 'get_property_report_data'}),
        name='property_report_data'
    ),
    re_path(
        r'^get_aggregated_property_report_data/$',
        Report.as_view({'get': 'get_aggregated_property_report_data'}),
        name='aggregated_property_report_data'
    ),
    # re_path(
    #     r'^property/',
    #     UpdateInventoryLabelsAPIView.as_view(),
    #     {'inventory_type': 'property'},
    #     name="property_labels",
    # ),
    # re_path(
    #     r'^taxlot/$',
    #     UpdateInventoryLabelsAPIView.as_view(),
    #     {'inventory_type': 'taxlot'},
    #     name="taxlot_labels",
    # ),
]
