# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.conf.urls import include, re_path
from rest_framework_nested import routers

from seed.api.v2_1.views import PropertyViewSetV21
from seed.views.notes import NoteViewSet
from seed.views.scenarios import ScenarioViewSet
from seed.views.tax_lot_properties import TaxLotPropertyViewSet
from seed.views.taxlots import TaxLotViewSet

router = routers.SimpleRouter()
router.register(r'properties', PropertyViewSetV21, basename="properties")
router.register(r'taxlots', TaxLotViewSet, basename="taxlots")
router.register(r'scenarios', ScenarioViewSet, basename="scenarios")
router.register(r'tax_lot_properties', TaxLotPropertyViewSet, basename="tax_lot_properties")

properties_router = routers.NestedSimpleRouter(router, r'properties', lookup='properties')
properties_router.register(r'notes', NoteViewSet, basename='property-notes')

taxlots_router = routers.NestedSimpleRouter(router, r'taxlots', lookup='taxlots')
taxlots_router.register(r'notes', NoteViewSet, basename='taxlot-notes')

urlpatterns = [
    re_path(r'^', include(router.urls)),
    re_path(r'^', include(properties_router.urls)),
    re_path(r'^', include(taxlots_router.urls)),
]
