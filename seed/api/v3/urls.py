"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import include, re_path
from rest_framework import routers
from rest_framework_nested import routers as nested_routers

from seed.views.main import celery_queue
from seed.views.v3.access_levels import AccessLevelViewSet
from seed.views.v3.analyses import AnalysisViewSet
from seed.views.v3.analysis_messages import AnalysisMessageViewSet
from seed.views.v3.analysis_views import AnalysisPropertyViewViewSet
from seed.views.v3.audit_template import AuditTemplateViewSet
from seed.views.v3.audit_template_configs import AuditTemplateConfigViewSet
from seed.views.v3.building_files import BuildingFileViewSet
from seed.views.v3.column_list_profiles import ColumnListProfileViewSet
from seed.views.v3.column_mapping_profiles import ColumnMappingProfileViewSet
from seed.views.v3.columns import ColumnViewSet
from seed.views.v3.compliance_metrics import ComplianceMetricViewSet
from seed.views.v3.cycles import CycleViewSet
from seed.views.v3.data_logger import DataLoggerViewSet
from seed.views.v3.data_quality_check_rules import DataQualityCheckRuleViewSet
from seed.views.v3.data_quality_checks import DataQualityCheckViewSet
from seed.views.v3.data_views import DataViewViewSet
from seed.views.v3.datasets import DatasetViewSet
from seed.views.v3.derived_columns import DerivedColumnViewSet
from seed.views.v3.eeej import EEEJViewSet
from seed.views.v3.elements import ElementViewSet, OrgElementViewSet
from seed.views.v3.events import EventViewSet
from seed.views.v3.filter_group import FilterGroupViewSet
from seed.views.v3.gbr_properties import GBRPropertyViewSet
from seed.views.v3.geocode import GeocodeViewSet
from seed.views.v3.goal_notes import GoalNoteViewSet
from seed.views.v3.goals import GoalViewSet
from seed.views.v3.green_assessment_properties import GreenAssessmentPropertyViewSet
from seed.views.v3.green_assessment_urls import GreenAssessmentURLViewSet
from seed.views.v3.green_assessments import GreenAssessmentViewSet
from seed.views.v3.historical_notes import HistoricalNoteViewSet
from seed.views.v3.import_files import ImportFileViewSet
from seed.views.v3.inventory_group_mappings import InventoryGroupMappingViewSet
from seed.views.v3.inventory_groups import InventoryGroupViewSet
from seed.views.v3.label_inventories import LabelInventoryViewSet
from seed.views.v3.labels import LabelViewSet
from seed.views.v3.measures import MeasureViewSet
from seed.views.v3.media import MediaViewSet
from seed.views.v3.meter_readings import MeterReadingViewSet
from seed.views.v3.meters import MeterViewSet
from seed.views.v3.notes import NoteViewSet
from seed.views.v3.organization_users import OrganizationUserViewSet
from seed.views.v3.organizations import OrganizationViewSet
from seed.views.v3.portfolio_manager import PortfolioManagerViewSet
from seed.views.v3.postoffice import PostOfficeEmailViewSet, PostOfficeViewSet
from seed.views.v3.progress import ProgressViewSet
from seed.views.v3.properties import PropertyViewSet
from seed.views.v3.property_measures import PropertyMeasureViewSet
from seed.views.v3.property_scenarios import PropertyScenarioViewSet
from seed.views.v3.property_view_labels import PropertyViewLabelViewSet
from seed.views.v3.property_views import PropertyViewViewSet
from seed.views.v3.public import PublicCycleViewSet, PublicOrganizationViewSet
from seed.views.v3.salesforce_configs import SalesforceConfigViewSet
from seed.views.v3.salesforce_mappings import SalesforceMappingViewSet
from seed.views.v3.sensors import SensorViewSet
from seed.views.v3.systems import SystemViewSet
from seed.views.v3.tax_lot_properties import TaxLotPropertyViewSet
from seed.views.v3.taxlot_views import TaxlotViewViewSet
from seed.views.v3.taxlots import TaxlotViewSet
from seed.views.v3.two_factor_views import TwoFactorViewSet
from seed.views.v3.ubid import UbidViewSet
from seed.views.v3.uniformat import UniformatViewSet
from seed.views.v3.uploads import UploadViewSet
from seed.views.v3.users import UserViewSet

api_v3_router = routers.DefaultRouter()
api_v3_router.register(r"analyses", AnalysisViewSet, basename="analyses")
api_v3_router.register(r"audit_template", AuditTemplateViewSet, basename="audit_template")
api_v3_router.register(r"audit_template_configs", AuditTemplateConfigViewSet, basename="audit_template_configs")
api_v3_router.register(r"building_files", BuildingFileViewSet, basename="building_files")
api_v3_router.register(r"column_list_profiles", ColumnListProfileViewSet, basename="column_list_profiles")
api_v3_router.register(r"column_mapping_profiles", ColumnMappingProfileViewSet, basename="column_mapping_profiles")
api_v3_router.register(r"columns", ColumnViewSet, basename="columns")
api_v3_router.register(r"compliance_metrics", ComplianceMetricViewSet, basename="compliance_metrics")
api_v3_router.register(r"cycles", CycleViewSet, basename="cycles")
api_v3_router.register(r"data_loggers", DataLoggerViewSet, basename="data_logger")
api_v3_router.register(r"data_quality_checks", DataQualityCheckViewSet, basename="data_quality_checks")
api_v3_router.register(r"data_views", DataViewViewSet, basename="data_views")
api_v3_router.register(r"datasets", DatasetViewSet, basename="datasets")
api_v3_router.register(r"derived_columns", DerivedColumnViewSet, basename="derived_columns")
api_v3_router.register(r"eeej", EEEJViewSet, basename="eeej")
api_v3_router.register(r"elements", OrgElementViewSet, basename="elements")
api_v3_router.register(r"filter_groups", FilterGroupViewSet, basename="filter_groups")
api_v3_router.register(r"gbr_properties", GBRPropertyViewSet, basename="gbr_properties")
api_v3_router.register(r"goals", GoalViewSet, basename="goals")
api_v3_router.register(r"geocode", GeocodeViewSet, basename="geocode")
api_v3_router.register(r"green_assessment_properties", GreenAssessmentPropertyViewSet, basename="green_assessment_properties")
api_v3_router.register(r"green_assessment_urls", GreenAssessmentURLViewSet, basename="green_assessment_urls")
api_v3_router.register(r"green_assessments", GreenAssessmentViewSet, basename="green_assessments")
api_v3_router.register(r"import_files", ImportFileViewSet, basename="import_files")
api_v3_router.register(r"inventory_groups", InventoryGroupViewSet, basename="inventory_groups")
api_v3_router.register(r"inventory_group_mappings", InventoryGroupMappingViewSet, basename="inventory_group_mappings")
api_v3_router.register(r"labels", LabelViewSet, basename="labels")
api_v3_router.register(r"measures", MeasureViewSet, basename="measures")
api_v3_router.register(r"organizations", OrganizationViewSet, basename="organizations")
api_v3_router.register(r"portfolio_manager", PortfolioManagerViewSet, basename="portfolio_manager")
api_v3_router.register(r"postoffice", PostOfficeViewSet, basename="postoffice")
api_v3_router.register(r"postoffice_email", PostOfficeEmailViewSet, basename="postoffice_email")
api_v3_router.register(r"progress", ProgressViewSet, basename="progress")
api_v3_router.register(r"properties", PropertyViewSet, basename="properties")
api_v3_router.register(r"property_view_labels", PropertyViewLabelViewSet, basename="property_view_labels")
api_v3_router.register(r"property_views", PropertyViewViewSet, basename="property_views")
api_v3_router.register(r"salesforce_configs", SalesforceConfigViewSet, basename="salesforce_configs")
api_v3_router.register(r"salesforce_mappings", SalesforceMappingViewSet, basename="salesforce_mappings")
api_v3_router.register(r"tax_lot_properties", TaxLotPropertyViewSet, basename="tax_lot_properties")
api_v3_router.register(r"taxlot_views", TaxlotViewViewSet, basename="taxlot_views")
api_v3_router.register(r"taxlots", TaxlotViewSet, basename="taxlots")
api_v3_router.register(r"two_factor", TwoFactorViewSet, basename="two_factor")
api_v3_router.register(r"ubid", UbidViewSet, basename="ubid")
api_v3_router.register(r"uniformat", UniformatViewSet, basename="uniformat")
api_v3_router.register(r"upload", UploadViewSet, basename="upload")
api_v3_router.register(r"users", UserViewSet, basename="user")

data_quality_checks_router = nested_routers.NestedSimpleRouter(api_v3_router, r"data_quality_checks", lookup="nested")
data_quality_checks_router.register(r"rules", DataQualityCheckRuleViewSet, basename="data_quality_check-rules")

organizations_router = nested_routers.NestedSimpleRouter(api_v3_router, r"organizations", lookup="organization")
organizations_router.register(r"users", OrganizationUserViewSet, basename="organization-users")
organizations_router.register(r"access_levels", AccessLevelViewSet, basename="organization-access_levels")

analysis_views_router = nested_routers.NestedSimpleRouter(api_v3_router, r"analyses", lookup="analysis")
analysis_views_router.register(r"views", AnalysisPropertyViewViewSet, basename="analysis-views")

analysis_messages_router = nested_routers.NestedSimpleRouter(api_v3_router, r"analyses", lookup="analysis")
analysis_messages_router.register(r"messages", AnalysisMessageViewSet, basename="analysis-messages")

analysis_view_messages_router = nested_routers.NestedSimpleRouter(analysis_views_router, r"views", lookup="views")
analysis_view_messages_router.register(r"views_messages", AnalysisMessageViewSet, basename="analysis-messages")

properties_router = nested_routers.NestedSimpleRouter(api_v3_router, r"properties", lookup="property")
properties_router.register(r"meters", MeterViewSet, basename="property-meters")
properties_router.register(r"notes", NoteViewSet, basename="property-notes")
properties_router.register(r"elements", ElementViewSet, basename="property-elements")
properties_router.register(r"scenarios", PropertyScenarioViewSet, basename="property-scenarios")
properties_router.register(r"events", EventViewSet, basename="property-events")
properties_router.register(r"goal_notes", GoalNoteViewSet, basename="property-goal-notes")
properties_router.register(r"historical_notes", HistoricalNoteViewSet, basename="property-historical-notes")
properties_router.register(r"sensors", SensorViewSet, basename="property-sensors")

inventory_group_router = nested_routers.NestedSimpleRouter(api_v3_router, r"inventory_groups", lookup="inventory_group")
inventory_group_router.register(r"systems", SystemViewSet, basename="inventory_group-systems")

# This is a third level router, so we need to register it with the second level router
meters_router = nested_routers.NestedSimpleRouter(properties_router, r"meters", lookup="meter")
meters_router.register(r"readings", MeterReadingViewSet, basename="property-meter-readings")


property_measures_router = nested_routers.NestedSimpleRouter(properties_router, r"scenarios", lookup="scenario")
property_measures_router.register(r"measures", PropertyMeasureViewSet, basename="property-measures")

taxlots_router = nested_routers.NestedSimpleRouter(api_v3_router, r"taxlots", lookup="taxlot")
taxlots_router.register(r"notes", NoteViewSet, basename="taxlot-notes")

public_organizations_router = routers.DefaultRouter()
public_organizations_router.register(
    r"public/organizations",
    PublicOrganizationViewSet,
    basename="public-organizations",
)

public_cycles_router = nested_routers.NestedSimpleRouter(public_organizations_router, r"public/organizations", lookup="organization")
public_cycles_router.register(r"cycles", PublicCycleViewSet, basename="public-organizations-cycles")

urlpatterns = [
    re_path(r"^", include(api_v3_router.urls)),
    re_path(r"^", include(data_quality_checks_router.urls)),
    re_path(
        r"^labels_property/$",
        LabelInventoryViewSet.as_view(),
        {"inventory_type": "property"},
    ),
    re_path(
        r"^labels_taxlot/$",
        LabelInventoryViewSet.as_view(),
        {"inventory_type": "taxlot"},
    ),
    re_path(r"^", include(organizations_router.urls)),
    re_path(r"^", include(analysis_views_router.urls)),
    re_path(r"^", include(analysis_messages_router.urls)),
    re_path(r"^", include(analysis_view_messages_router.urls)),
    re_path(r"^", include(properties_router.urls)),
    re_path(r"^", include(meters_router.urls)),
    re_path(r"^", include(property_measures_router.urls)),
    re_path(r"^", include(taxlots_router.urls)),
    re_path(r"^", include(inventory_group_router.urls)),
    re_path(r"^", include(public_organizations_router.urls)),
    re_path(r"^", include(public_cycles_router.urls)),
    re_path(r"^celery_queue/$", celery_queue, name="celery_queue"),
    re_path(r"media/(?P<filepath>.*)$", MediaViewSet.as_view()),
]
