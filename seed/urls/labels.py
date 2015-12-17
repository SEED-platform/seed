# !/usr/bin/env python
# encoding: utf-8
"""
Url patterns for endpoints associated with Labels
:copyright (c) 2015, The Regents of the University of California, Department of Energy contract-operators of the Lawrence Berkeley National Laboratory.  # NOQA
:author Piper Merriam
"""

from django.conf.urls import url

from rest_framework import routers

from seed.views.labels import (
    LabelViewSet,
    UpdateBuildingLabelsAPIView,
)


router = routers.SimpleRouter()
router.register(r'', LabelViewSet, base_name="label")


urlpatterns = [
    url(
        r'^/update-building-labels/$',
        UpdateBuildingLabelsAPIView.as_view(),
        name="update_building_labels",
    ),
]


urlpatterns += router.urls
