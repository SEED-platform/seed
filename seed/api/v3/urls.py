# !/usr/bin/env python
# encoding: utf-8
from django.conf.urls import url, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from seed.views.v3.column_mapping_profiles import ColumnMappingProfileViewSet
from seed.views.v3.columns import ColumnViewSet
from seed.views.v3.cycles import CycleViewSet
from seed.views.v3.data_quality_checks import DataQualityCheckViewSet
from seed.views.v3.data_quality_check_rules import DataQualityCheckRuleViewSet
from seed.views.v3.datasets import DatasetViewSet
from seed.views.v3.labels import LabelViewSet
from seed.views.v3.import_files import ImportFileViewSet
from seed.views.v3.measures import MeasureViewSet
from seed.views.v3.meters import MeterViewSet
from seed.views.v3.organizations import OrganizationViewSet
from seed.views.v3.organization_users import OrganizationUserViewSet
from seed.views.v3.properties import PropertyViewSet
from seed.views.v3.taxlots import TaxlotViewSet
from seed.views.v3.uploads import UploadViewSet
from seed.views.v3.users import UserViewSet

api_v3_router = routers.DefaultRouter()
api_v3_router.register(r'column_mapping_profiles', ColumnMappingProfileViewSet, base_name='column_mapping_profiles')
api_v3_router.register(r'columns', ColumnViewSet, base_name='columns')
api_v3_router.register(r'cycles', CycleViewSet, base_name='cycles')
api_v3_router.register(r'datasets', DatasetViewSet, base_name='datasets')
api_v3_router.register(r'labels', LabelViewSet, base_name='labels')
api_v3_router.register(r'data_quality_checks', DataQualityCheckViewSet, base_name='data_quality_checks')
api_v3_router.register(r'import_files', ImportFileViewSet, base_name='import_files')
api_v3_router.register(r'measures', MeasureViewSet, base_name='import_files')
api_v3_router.register(r'meters', MeterViewSet, base_name='meters')
api_v3_router.register(r'organizations', OrganizationViewSet, base_name='organizations')
api_v3_router.register(r'properties', PropertyViewSet, base_name='properties')
api_v3_router.register(r'taxlots', TaxlotViewSet, base_name='taxlots')
api_v3_router.register(r'upload', UploadViewSet, base_name='upload')
api_v3_router.register(r'users', UserViewSet, base_name='user')

data_quality_checks_router = nested_routers.NestedSimpleRouter(api_v3_router, r'data_quality_checks', lookup="nested")
data_quality_checks_router.register(r'rules', DataQualityCheckRuleViewSet, base_name='data_quality_check-rules')

organizations_router = nested_routers.NestedSimpleRouter(api_v3_router, r'organizations', lookup='organization')
organizations_router.register(r'users', OrganizationUserViewSet, base_name='organization-users')

urlpatterns = [
    url(r'^', include(api_v3_router.urls)),
    url(r'^', include(data_quality_checks_router.urls)),
    url(r'^', include(organizations_router.urls)),
]
