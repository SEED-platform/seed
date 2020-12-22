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
from seed.views.v3.gbr_properties import GBRPropertyViewSet
from seed.views.v3.geocode import GeocodeViewSet
from seed.views.v3.green_assessment_properties import GreenAssessmentPropertyViewSet
from seed.views.v3.green_assessment_urls import GreenAssessmentURLViewSet
from seed.views.v3.green_assessments import GreenAssessmentViewSet
from seed.views.v3.import_files import ImportFileViewSet
from seed.views.v3.measures import MeasureViewSet
from seed.views.v3.labels import LabelViewSet
from seed.views.v3.label_inventories import LabelInventoryViewSet
from seed.views.v3.meters import MeterViewSet
from seed.views.v3.notes import NoteViewSet
from seed.views.v3.organizations import OrganizationViewSet
from seed.views.v3.organization_users import OrganizationUserViewSet
from seed.views.v3.portfolio_manager import PortfolioManagerViewSet
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
api_v3_router.register(r'analyses', AnalysisViewSet, base_name='analyses')
api_v3_router.register(r'building_files', BuildingFileViewSet, base_name="building_files")
api_v3_router.register(r'column_list_profiles', ColumnListProfileViewSet, base_name="column_list_profiles")
api_v3_router.register(r'column_mapping_profiles', ColumnMappingProfileViewSet, base_name='column_mapping_profiles')
api_v3_router.register(r'columns', ColumnViewSet, base_name='columns')
api_v3_router.register(r'cycles', CycleViewSet, base_name='cycles')
api_v3_router.register(r'datasets', DatasetViewSet, base_name='datasets')
api_v3_router.register(r'gbr_properties', GBRPropertyViewSet, base_name="properties")
api_v3_router.register(r'geocode', GeocodeViewSet, base_name='geocode')
api_v3_router.register(r'green_assessment_properties', GreenAssessmentPropertyViewSet, base_name="green_assessment_properties")
api_v3_router.register(r'green_assessment_urls', GreenAssessmentURLViewSet, base_name="green_assessment_urls")
api_v3_router.register(r'green_assessments', GreenAssessmentViewSet, base_name="green_assessments")
api_v3_router.register(r'labels', LabelViewSet, base_name='labels')
api_v3_router.register(r'data_quality_checks', DataQualityCheckViewSet, base_name='data_quality_checks')
api_v3_router.register(r'import_files', ImportFileViewSet, base_name='import_files')
api_v3_router.register(r'measures', MeasureViewSet, base_name='measures')
api_v3_router.register(r'meters', MeterViewSet, base_name='meters')
api_v3_router.register(r'organizations', OrganizationViewSet, base_name='organizations')
api_v3_router.register(r'portfolio_manager', PortfolioManagerViewSet, base_name="portfolio_manager")
api_v3_router.register(r'progress', ProgressViewSet, base_name="progress")
api_v3_router.register(r'properties', PropertyViewSet, base_name='properties')
api_v3_router.register(r'property_states', PropertyStateViewSet, base_name="property_states")
api_v3_router.register(r'property_views', PropertyViewViewSet, base_name="property_views")
api_v3_router.register(r'tax_lot_properties', TaxLotPropertyViewSet, base_name="tax_lot_properties")
api_v3_router.register(r'taxlots', TaxlotViewSet, base_name='taxlots')
api_v3_router.register(r'ubid', UbidViewSet, base_name='ubid')
api_v3_router.register(r'upload', UploadViewSet, base_name='upload')
api_v3_router.register(r'users', UserViewSet, base_name='user')

data_quality_checks_router = nested_routers.NestedSimpleRouter(api_v3_router, r'data_quality_checks', lookup="nested")
data_quality_checks_router.register(r'rules', DataQualityCheckRuleViewSet, base_name='data_quality_check-rules')

organizations_router = nested_routers.NestedSimpleRouter(api_v3_router, r'organizations', lookup='organization')
organizations_router.register(r'users', OrganizationUserViewSet, base_name='organization-users')

analysis_views_router = nested_routers.NestedSimpleRouter(api_v3_router, r'analyses', lookup='analysis')
analysis_views_router.register(r'views', AnalysisPropertyViewViewSet, base_name='analysis-views')

analysis_messages_router = nested_routers.NestedSimpleRouter(api_v3_router, r'analyses', lookup='analysis')
analysis_messages_router.register(r'messages', AnalysisMessageViewSet, base_name='analysis-messages')

analysis_view_messages_router = nested_routers.NestedSimpleRouter(analysis_views_router, r'views', lookup='views')
analysis_view_messages_router.register(r'views_messages', AnalysisMessageViewSet, base_name='analysis-messages')

properties_router = nested_routers.NestedSimpleRouter(api_v3_router, r'properties', lookup='property')
properties_router.register(r'notes', NoteViewSet, base_name='property-notes')
properties_router.register(r'scenarios', PropertyScenarioViewSet, base_name='property-scenarios')

taxlots_router = nested_routers.NestedSimpleRouter(api_v3_router, r'taxlots', lookup='taxlot')
taxlots_router.register(r'notes', NoteViewSet, base_name='taxlot-notes')


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
]
