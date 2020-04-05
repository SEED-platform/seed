# !/usr/bin/env python
# encoding: utf-8
from django.conf.urls import url, include
from rest_framework import routers

from seed.views.data_quality import DataQualityViews

dq_v3_router = routers.DefaultRouter()
dq_v3_router.register(r'data_quality_checks', DataQualityViews, base_name='data_quality_checks')

dq_urlpatterns = [
    url(r'^', include(dq_v3_router.urls)),
]

urlpatterns = [
    url(r'', include((dq_urlpatterns, 'seed'), namespace='data_quality_checks')),
]
