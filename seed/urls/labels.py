# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'

Url patterns for endpoints associated with Labels
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
        r'^property/',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'property'},
        name="property_labels",
    ),
    url(
        r'^taxlot-labels/$',
        UpdateInventoryLabelsAPIView.as_view(),
        {'inventory_type': 'taxlot'},
        name="taxlot_labels",
    ),
]


urlpatterns += router.urls
