# !/usr/bin/env python
# encoding: utf-8
from django.conf.urls import url, include
from rest_framework import routers

from seed.views.v3.cycles import CycleViewSet
from seed.views.v3.datasets import DatasetViewSet
from seed.views.v3.labels import LabelViewSet
from seed.views.v3.labels import UpdateInventoryLabelsAPIView
from seed.views.v3.data_quality import DataQualityViews


api_v3_router = routers.DefaultRouter()
api_v3_router.register(r'cycles', CycleViewSet, base_name='cycles')
api_v3_router.register(r'datasets', DatasetViewSet, base_name='datasets')
api_v3_router.register(r'labels', LabelViewSet, base_name='labels')
api_v3_router.register(r'data_quality_checks', DataQualityViews, base_name='data_quality_checks')


urlpatterns = [
    url(r'^', include(api_v3_router.urls)),
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
]
