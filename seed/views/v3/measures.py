"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Measure
from seed.serializers.measures import MeasureSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param


@method_decorator(
    name="retrieve",
    decorator=[
        has_perm_class("can_view_data"),
        swagger_auto_schema_org_query_param,
    ],
)
@method_decorator(
    name="list",
    decorator=[
        has_perm_class("can_view_data"),
        swagger_auto_schema_org_query_param,
    ],
)
class MeasureViewSet(viewsets.ReadOnlyModelViewSet, OrgMixin):
    """
    list:
        Return a list of all measures

    retrieve:
        Return a measure by a unique id

    """

    serializer_class = MeasureSerializer
    parser_classes = (
        JSONParser,
        FormParser,
    )
    renderer_classes = (JSONRenderer,)
    pagination_class = None

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        # TODO: there could be multiple versions of each measure. Do we retrieve them all or a specific version of them?
        # TODO: I set this to latest version for now. I'm not sure this functionality is used.
        return Measure.objects.filter(organization_id=org_id, schema_version="2.6.0")

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()], request_body=no_body)
    @has_perm_class("can_modify_data")
    @action(detail=False, methods=["POST"])
    def reset(self, request):
        """
        Reset all the measures back to the defaults (as provided by BuildingSync)
        """
        organization_id = self.get_organization(request)
        if not organization_id:
            return JsonResponse({"status": "error", "message": "organization_id not provided"}, status=status.HTTP_400_BAD_REQUEST)

        Measure.populate_measures(organization_id)  # this will repopulate the default buildingsync version
        Measure.populate_measures(organization_id, schema_version="2.6.0")  # also repopulate the latest version
        # TODO: this should be improved!
        data = {
            "measures": list(Measure.objects.filter(organization_id=organization_id).order_by("id").values()),
            "status": "success",
        }

        return JsonResponse(data)
