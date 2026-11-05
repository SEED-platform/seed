"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_serializer, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.filters import LabelFilterBackend
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import StatusLabel as Label
from seed.serializers.labels import LabelSerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

# The label attributes clients may set; the organization is always taken from the request
LABEL_ATTRIBUTES_SCHEMA = {
    "name": {"type": "string", "maxLength": 255},
    "color": {"type": "string", "enum": [color for color, _ in Label.COLOR_CHOICES]},
    "show_in_list": {"type": "boolean"},
}
label_body = {"application/json": {"type": "object", "properties": LABEL_ATTRIBUTES_SCHEMA, "required": ["name"]}}
optional_org_param = AutoSchemaHelper.query_org_id_field(
    required=False, description="Optional org id which overrides the users (default) current org id"
)


# Schema only: this viewset's labels are not annotated for inventory, so `is_applied*` are never returned
@extend_schema_serializer(exclude_fields=["is_applied", "is_applied_by_goal"])
class LabelResponseSerializer(LabelSerializer):
    pass


@extend_schema_view(
    retrieve=extend_schema(
        description="Return a label instance by pk if it is within user`s specified org.",
        parameters=[optional_org_param],
        responses=LabelResponseSerializer,
    ),
    list=extend_schema(
        description="Return all labels available to user through user`s specified org.",
        parameters=[optional_org_param],
        responses=LabelResponseSerializer(many=True),
    ),
    create=extend_schema(
        description="Create a new label within user`s specified org.",
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=label_body,
        responses={201: LabelResponseSerializer},
    ),
    destroy=extend_schema(
        description="Remove an existing label.",
        parameters=[AutoSchemaHelper.query_org_id_field()],
    ),
    update=extend_schema(
        description="Update a label record.",
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=label_body,
        responses=LabelResponseSerializer,
    ),
)
@method_decorator(
    [
        has_perm("requires_root_member_access"),
    ],
    name="create",
)
@method_decorator(
    [
        has_perm("requires_root_member_access"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_root_member_access"),
    ],
    name="update",
)
class LabelViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for viewing and managing the labels of an organization"""

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

    @extend_schema_org_query_param
    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "label_ids": {"type": "array", "items": {"type": "integer"}, "description": "IDs of the organization's labels"},
                    "data": {"type": "object", "properties": LABEL_ATTRIBUTES_SCHEMA, "description": "Attributes to set on each label"},
                },
                "required": ["label_ids", "data"],
            }
        },
        responses={
            200: AutoSchemaHelper.schema_factory({}),
            400: OpenApiResponse(description="Missing or invalid arguments"),
        },
    )
    @method_decorator(
        [
            has_perm("requires_root_member_access"),
        ]
    )
    @action(detail=False, methods=["PUT"])
    def bulk_update(self, request):
        """Set the same attributes on several labels of the organization"""
        organization_id = self.get_parent_org(self.request)
        label_ids = request.data.get("label_ids")
        data = request.data.get("data")
        if not organization_id or not label_ids or not data:
            return JsonResponse({"status": "error", "message": "Missing required arguments"}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(data, dict) or not data.keys() <= LABEL_ATTRIBUTES_SCHEMA.keys():
            return JsonResponse(
                {"status": "error", "message": f"data may only contain: {', '.join(LABEL_ATTRIBUTES_SCHEMA)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        labels = Label.objects.filter(id__in=label_ids, super_organization=organization_id)
        try:
            with transaction.atomic():
                labels.update(**data)
                return JsonResponse({})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
