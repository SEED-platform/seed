# !/usr/bin/env python
# encoding: utf-8
from django.conf.urls import url, include
from rest_framework import routers

from seed.views.v3.columns import ColumnViewSet
from seed.views.v3.cycles import CycleViewSet
from seed.views.v3.datasets import DatasetViewSet
from seed.views.v3.data_quality import DataQualityViews
from seed.views.v3.import_files import ImportFileViewSet
from seed.views.v3.organizations import OrganizationViewSet
from seed.views.v3.users import UserViewSet

api_v3_router = routers.DefaultRouter()
api_v3_router.register(r'columns', ColumnViewSet, base_name='columns')
api_v3_router.register(r'cycles', CycleViewSet, base_name='cycles')
api_v3_router.register(r'datasets', DatasetViewSet, base_name='datasets')
api_v3_router.register(r'data_quality_checks', DataQualityViews, base_name='data_quality_checks')
api_v3_router.register(r'import_files', ImportFileViewSet, base_name='import_files')
api_v3_router.register(r'organizations', OrganizationViewSet, base_name='organizations')
api_v3_router.register(r'users', UserViewSet, base_name='user')

urlpatterns = [
    url(r'^', include(api_v3_router.urls)),
]
