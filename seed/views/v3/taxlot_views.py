"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.lib.superperms.orgs.permissions import get_org_id
from seed.models import TaxLotView
from seed.serializers.taxlots import BriefTaxlotViewSerializer
from seed.utils.api import OrgMixin, ProfileIdMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


class TaxlotViewViewSet(viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("taxlot", required=False, description="Only return the views of this tax lot ID"),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "taxlot_views": [
                        {
                            "id": "integer",
                            "taxlot_id": "integer",
                            "cycle": {
                                "id": "integer",
                                "name": "string",
                                "start": "date",
                                "end": "date",
                                "created": "datetime",
                                "organization": "integer",
                                "user": "integer",
                            },
                        }
                    ],
                }
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def list(self, request):
        """
        List all the taxlots
        """
        # the organization that `has_perm` authorized
        org_id = get_org_id(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        if not org_id:
            return JsonResponse(
                {"status": "error", "message": "Need to pass organization_id as query parameter"}, status=status.HTTP_400_BAD_REQUEST
            )

        views = TaxLotView.objects.filter(
            taxlot__organization_id=org_id,
            taxlot__access_level_instance__lft__gte=access_level_instance.lft,
            taxlot__access_level_instance__rgt__lte=access_level_instance.rgt,
        )

        taxlot = request.query_params.get("taxlot")
        if taxlot is not None:
            views = views.filter(taxlot_id=taxlot)

        return {"status": "success", "taxlot_views": [BriefTaxlotViewSerializer(view).data for view in views]}
