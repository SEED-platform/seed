# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Element
from seed.serializers.elements import ElementSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgReadOnlyModelViewSet


@method_decorator(
    name="list",
    decorator=[
        swagger_auto_schema_org_query_param,
        # TODO change
        has_perm_class("requires_root_member_access"),
    ],
)
@method_decorator(
    name="retrieve",
    decorator=[
        swagger_auto_schema_org_query_param,
        # TODO change
        has_perm_class("requires_root_member_access"),
    ],
)
class OrgElementViewSet(SEEDOrgReadOnlyModelViewSet):
    """
    API view for Elements belong to an entire organization
    """

    serializer_class = ElementSerializer
    model = Element
    data_name = "elements"
