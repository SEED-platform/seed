"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.filters import LabelFilterBackend
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import StatusLabel as Label
from seed.serializers.labels import LabelSerializer
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Optional org id which overrides the users (default) current org id"
            )
        ]
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Optional org id which overrides the users (default) current org id"
            )
        ]
    ),
)
@method_decorator(
    name="create",
    decorator=[
        swagger_auto_schema(
            manual_parameters=[
                AutoSchemaHelper.query_org_id_field(
                    required=False, description="Optional org id which overrides the users (default) current org id"
                )
            ],
            request_body=AutoSchemaHelper.schema_factory(
                {
                    "name": "string",
                    "color": "string",
                },
                required=["name"],
                description="An object containing meta data for a new label",
            ),
        ),
        has_perm_class("requires_root_member_access"),
    ],
)
@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema(
            manual_parameters=[
                AutoSchemaHelper.query_org_id_field(
                    required=False, description="Optional org id which overrides the users (default) current org id"
                )
            ]
        ),
        has_perm_class("requires_root_member_access"),
    ],
)
@method_decorator(
    name="update",
    decorator=[
        has_perm_class("requires_root_member_access"),
        swagger_auto_schema(
            manual_parameters=[
                AutoSchemaHelper.query_org_id_field(
                    required=False, description="Optional org id which overrides the users (default) current org id"
                )
            ],
            request_body=AutoSchemaHelper.schema_factory(
                {
                    "name": "string",
                    "color": "string",
                },
                required=["name"],
                description="An object containing meta data for updating a label",
            ),
        ),
    ],
)
class LabelViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    retrieve:
        Return a label instance by pk if it is within user`s specified org.

    list:
        Return all labels available to user through user`s specified org.

    create:
        Create a new label within user`s specified org.

    delete:
        Remove an existing label.

    update:
        Update a label record.
    """

    serializer_class = LabelSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser, FormParser)
    queryset = Label.objects.none()
    filter_backends = (LabelFilterBackend,)
    pagination_class = None
    _organization = None

    def get_queryset(self):
        labels = Label.objects.filter(super_organization=self.get_parent_org(self.request)).order_by("name").distinct()
        return labels

    def get_serializer(self, *args, **kwargs):
        kwargs["super_organization"] = self.get_organization(self.request)
        return super().get_serializer(*args, **kwargs)

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_root_member_access")
    @action(detail=False, methods=["PUT"])
    def bulk_update(self, request):
        organization_id = self.get_parent_org(self.request)
        label_ids = request.data.get("label_ids")
        data = request.data.get("data")
        if not organization_id or not label_ids or not data:
            return JsonResponse({"status": "error", "message": "Missing required arguments"}, status=status.HTTP_400_BAD_REQUETS)

        labels = Label.objects.filter(id__in=label_ids, super_organization=organization_id)
        try:
            with transaction.atomic():
                labels.update(**data)
                return JsonResponse({})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUETS)
