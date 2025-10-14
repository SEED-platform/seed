"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import include, path
from rest_framework import routers

from seed.views.v4.analyses import AnalysisViewSet
from seed.views.v4.organization_users import OrganizationUserViewSet
from seed.views.v4.taxlot_properties import TaxLotPropertyViewSet

api_v4_router = routers.DefaultRouter()
api_v4_router.register(r"analyses", AnalysisViewSet, basename="analyses")
api_v4_router.register(r"organization_users", OrganizationUserViewSet, basename="organization_users")
api_v4_router.register(r"tax_lot_properties", TaxLotPropertyViewSet, basename="tax_lot_properties")


urlpatterns = [
    path("", include(api_v4_router.urls)),
]
