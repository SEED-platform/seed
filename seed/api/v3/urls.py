# !/usr/bin/env python
# encoding: utf-8
from django.conf.urls import url, include

from rest_framework import routers

from rest_framework_nested import routers as nested_routers

from seed.views.v3.analyses import AnalysisViewSet
from seed.views.v3.analysis_messages import AnalysisMessageViewSet
from seed.views.v3.analysis_views import AnalysisPropertyViewViewSet
from seed.views.v3.building_files import BuildingFileViewSet
from seed.views.v3.column_list_profiles import ColumnListProfileViewSet
from seed.views.v3.column_mapping_profiles import ColumnMappingProfileViewSet
from seed.views.v3.columns import ColumnViewSet
from seed.views.v3.cycles import CycleViewSet
from seed.views.v3.data_quality_checks import DataQualityCheckViewSet
from seed.views.v3.data_quality_check_rules import DataQualityCheckRuleViewSet
from seed.views.v3.datasets import DatasetViewSet
from seed.views.v3.derived_columns import DerivedColumnViewSet
from seed.views.v3.gbr_properties import GBRPropertyViewSet
from seed.views.v3.geocode import GeocodeViewSet
from seed.views.v3.green_assessment_properties import GreenAssessmentPropertyViewSet
from seed.views.v3.green_assessment_urls import GreenAssessmentURLViewSet
from seed.views.v3.green_assessments import GreenAssessmentViewSet
from seed.views.v3.import_files import ImportFileViewSet
from seed.views.v3.measures import MeasureViewSet
from seed.views.v3.labels import LabelViewSet
from seed.views.v3.label_inventories import LabelInventoryViewSet
from seed.views.v3.media import MediaViewSet
from seed.views.v3.meters import MeterViewSet
from seed.views.v3.notes import NoteViewSet
from seed.views.v3.organizations import OrganizationViewSet
from seed.views.v3.organization_users import OrganizationUserViewSet
from seed.views.v3.portfolio_manager import PortfolioManagerViewSet
from seed.views.v3.postoffice import PostOfficeViewSet, PostOfficeEmailViewSet
from seed.views.v3.progress import ProgressViewSet
from seed.views.v3.properties import PropertyViewSet
from seed.views.v3.property_states import PropertyStateViewSet
from seed.views.v3.property_views import PropertyViewViewSet
from seed.views.v3.property_scenarios import PropertyScenarioViewSet
from seed.views.v3.tax_lot_properties import TaxLotPropertyViewSet
from seed.views.v3.taxlots import TaxlotViewSet
from seed.views.v3.ubid import UbidViewSet
from seed.views.v3.uploads import UploadViewSet
from seed.views.v3.users import UserViewSet

api_v3_router = routers.DefaultRouter()
api_v3_router.register(r'analyses', AnalysisViewSet, basename='analyses')
api_v3_router.register(r'building_files', BuildingFileViewSet, basename="building_files")
api_v3_router.register(r'column_list_profiles', ColumnListProfileViewSet, basename="column_list_profiles")
api_v3_router.register(r'column_mapping_profiles', ColumnMappingProfileViewSet, basename='column_mapping_profiles')
api_v3_router.register(r'columns', ColumnViewSet, basename='columns')
api_v3_router.register(r'cycles', CycleViewSet, basename='cycles')
api_v3_router.register(r'datasets', DatasetViewSet, basename='datasets')
api_v3_router.register(r'derived_columns', DerivedColumnViewSet, basename='derived_columns')
api_v3_router.register(r'gbr_properties', GBRPropertyViewSet, basename="properties")
api_v3_router.register(r'geocode', GeocodeViewSet, basename='geocode')
api_v3_router.register(r'green_assessment_properties', GreenAssessmentPropertyViewSet, basename="green_assessment_properties")
api_v3_router.register(r'green_assessment_urls', GreenAssessmentURLViewSet, basename="green_assessment_urls")
api_v3_router.register(r'green_assessments', GreenAssessmentViewSet, basename="green_assessments")
api_v3_router.register(r'labels', LabelViewSet, basename='labels')
api_v3_router.register(r'data_quality_checks', DataQualityCheckViewSet, basename='data_quality_checks')
api_v3_router.register(r'import_files', ImportFileViewSet, basename='import_files')
api_v3_router.register(r'measures', MeasureViewSet, basename='measures')
api_v3_router.register(r'meters', MeterViewSet, basename='meters')
api_v3_router.register(r'organizations', OrganizationViewSet, basename='organizations')
api_v3_router.register(r'portfolio_manager', PortfolioManagerViewSet, basename="portfolio_manager")
api_v3_router.register(r'postoffice', PostOfficeViewSet, basename='postoffice')
api_v3_router.register(r'postoffice_email', PostOfficeEmailViewSet, basename='postoffice_email')
api_v3_router.register(r'progress', ProgressViewSet, basename="progress")
api_v3_router.register(r'properties', PropertyViewSet, basename='properties')
api_v3_router.register(r'property_states', PropertyStateViewSet, basename="property_states")
api_v3_router.register(r'property_views', PropertyViewViewSet, basename="property_views")
api_v3_router.register(r'tax_lot_properties', TaxLotPropertyViewSet, basename="tax_lot_properties")
api_v3_router.register(r'taxlots', TaxlotViewSet, basename='taxlots')
api_v3_router.register(r'ubid', UbidViewSet, basename='ubid')
api_v3_router.register(r'upload', UploadViewSet, basename='upload')
api_v3_router.register(r'users', UserViewSet, basename='user')

data_quality_checks_router = nested_routers.NestedSimpleRouter(api_v3_router, r'data_quality_checks', lookup="nested")
data_quality_checks_router.register(r'rules', DataQualityCheckRuleViewSet, basename='data_quality_check-rules')

organizations_router = nested_routers.NestedSimpleRouter(api_v3_router, r'organizations', lookup='organization')
organizations_router.register(r'users', OrganizationUserViewSet, basename='organization-users')

analysis_views_router = nested_routers.NestedSimpleRouter(api_v3_router, r'analyses', lookup='analysis')
analysis_views_router.register(r'views', AnalysisPropertyViewViewSet, basename='analysis-views')

analysis_messages_router = nested_routers.NestedSimpleRouter(api_v3_router, r'analyses', lookup='analysis')
analysis_messages_router.register(r'messages', AnalysisMessageViewSet, basename='analysis-messages')

analysis_view_messages_router = nested_routers.NestedSimpleRouter(analysis_views_router, r'views', lookup='views')
analysis_view_messages_router.register(r'views_messages', AnalysisMessageViewSet, basename='analysis-messages')

properties_router = nested_routers.NestedSimpleRouter(api_v3_router, r'properties', lookup='property')
properties_router.register(r'notes', NoteViewSet, basename='property-notes')
properties_router.register(r'scenarios', PropertyScenarioViewSet, basename='property-scenarios')

taxlots_router = nested_routers.NestedSimpleRouter(api_v3_router, r'taxlots', lookup='taxlot')
taxlots_router.register(r'notes', NoteViewSet, basename='taxlot-notes')


urlpatterns = [
    url(r'^', include(api_v3_router.urls)),
    url(r'^', include(data_quality_checks_router.urls)),
    url(
        r'^labels_property/$',
        LabelInventoryViewSet.as_view(),
        {'inventory_type': 'property'},
    ),
    url(
        r'^labels_taxlot/$',
        LabelInventoryViewSet.as_view(),
        {'inventory_type': 'taxlot'},
    ),
    url(r'^', include(organizations_router.urls)),
    url(r'^', include(analysis_views_router.urls)),
    url(r'^', include(analysis_messages_router.urls)),
    url(r'^', include(analysis_view_messages_router.urls)),
    url(r'^', include(properties_router.urls)),
    url(r'^', include(taxlots_router.urls)),
    url(r'media/(?P<filepath>.*)$', MediaViewSet.as_view()),
]
