"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import serializers, status

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import Organization
from seed.models import VIEW_LIST_INVENTORY_TYPE, FilterGroup
from seed.models.models import StatusLabel
from seed.serializers.filter_groups import FilterGroupSerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

INVENTORY_TYPES = [name for _, name in VIEW_LIST_INVENTORY_TYPE]
FILTER_GROUP_FIELDS = {
    "name": "string",
    "inventory_type": tuple(VIEW_LIST_INVENTORY_TYPE),
    "query_dict": "object",
    "and_labels": ["integer"],
    "or_labels": ["integer"],
    "exclude_labels": ["integer"],
}


# Schema only: `FilterGroupSerializer` represents the inventory type by its name
class FilterGroupResponseSerializer(FilterGroupSerializer):
    inventory_type = serializers.ChoiceField(choices=INVENTORY_TYPES)


optional_org_param = AutoSchemaHelper.query_org_id_field(
    required=False, description="Optional org id which overrides the users (default) current org id"
)


def _get_inventory_type_int(inventory_type: str) -> int:
    return next(k for k, v in VIEW_LIST_INVENTORY_TYPE if v == inventory_type)


@extend_schema_view(
    retrieve=extend_schema(
        parameters=[optional_org_param],
        responses=FilterGroupResponseSerializer,
    ),
    destroy=extend_schema_org_query_param,
)
@method_decorator(
    [
        has_perm("requires_root_member_access"),
    ],
    name="destroy",
)
class FilterGroupViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing the filter groups (saved inventory filters) of an organization"""

    model = FilterGroup
    serializer_class = FilterGroupSerializer

    @extend_schema_org_query_param
    @extend_schema(
        request=AutoSchemaHelper.json_body(FILTER_GROUP_FIELDS, required=["name", "inventory_type"]),
        responses={
            201: OpenApiResponse(
                FilterGroupResponseSerializer,
                description="The response also contains `warnings` (string) listing any label IDs that are not labels of the organization",
            ),
            400: OpenApiResponse(description="Missing or invalid arguments"),
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def create(self, request):
        org_id = self.get_organization(request)

        body = dict(request.data)
        name = body.get("name")
        inventory_type = body.get("inventory_type")
        query_dict = body.get("query_dict", {})
        and_label_ids = body.get("and_labels", [])
        or_label_ids = body.get("or_labels", [])
        exclude_label_ids = body.get("exclude_labels", [])

        if not name:
            return JsonResponse({"success": False, "message": "name is missing"}, status=status.HTTP_400_BAD_REQUEST)

        if not inventory_type:
            return JsonResponse({"success": False, "message": "inventory_type is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            inventory_type_int = _get_inventory_type_int(inventory_type)
        except StopIteration:
            return JsonResponse(
                {"success": False, "message": 'invalid "inventory_type" must be "Property" or "Tax Lot"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            filter_group = FilterGroup.objects.create(
                name=name,
                organization_id=org_id,
                inventory_type=inventory_type_int,
                query_dict=query_dict,
            )
        except IntegrityError as e:
            return JsonResponse({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        all_bad_label_ids = set()
        good_label_ids, bad_label_ids = self._get_labels(and_label_ids)
        all_bad_label_ids.update(bad_label_ids)
        filter_group.and_labels.add(*good_label_ids)

        good_label_ids, bad_label_ids = self._get_labels(or_label_ids)
        all_bad_label_ids.update(bad_label_ids)
        filter_group.or_labels.add(*good_label_ids)

        good_label_ids, bad_label_ids = self._get_labels(exclude_label_ids)
        all_bad_label_ids.update(bad_label_ids)
        filter_group.exclude_labels.add(*good_label_ids)

        result = {
            "status": "success",
            "data": FilterGroupSerializer(filter_group).data,
        }

        if len(all_bad_label_ids) > 0:
            result["warnings"] = f"labels with ids do not exist: {', '.join([str(id) for id in all_bad_label_ids])}"

        return JsonResponse(result, status=status.HTTP_201_CREATED)

    @extend_schema_org_query_param
    @extend_schema(
        request=AutoSchemaHelper.json_body(
            FILTER_GROUP_FIELDS,
            description="Only the given attributes are updated. If any of the label lists is given, the omitted label lists are cleared.",
        ),
        responses={
            200: FilterGroupResponseSerializer,
            400: OpenApiResponse(description="Invalid arguments"),
            404: OpenApiResponse(description="Filter group not found"),
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk=None):
        filter_group = self.get_object()

        if "name" in request.data:
            filter_group.name = request.data["name"]

        if "query_dict" in request.data:
            filter_group.query_dict = request.data["query_dict"]

        if "inventory_type" in request.data:
            try:
                inventory_type_int = _get_inventory_type_int(request.data["inventory_type"])
            except StopIteration:
                return JsonResponse(
                    {"success": False, "message": 'invalid "inventory_type" must be "Property" or "Tax Lot"'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                filter_group.inventory_type = inventory_type_int

        if "and_labels" in request.data or "or_labels" in request.data or "exclude_labels" in request.data:
            _, bad_label_ids = self._get_labels(
                request.data.get("and_labels", []) + request.data.get("or_labels", []) + request.data.get("exclude_labels", [])
            )
            if bad_label_ids:
                return JsonResponse(
                    {"success": False, "message": f"invalid label ids: {', '.join([str(i) for i in set(bad_label_ids)])}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            filter_group.and_labels.set(request.data.get("and_labels", []))
            filter_group.or_labels.set(request.data.get("or_labels", []))
            filter_group.exclude_labels.set(request.data.get("exclude_labels", []))

        filter_group.save()

        result = {
            "status": "success",
            "data": FilterGroupSerializer(filter_group).data,
        }

        return JsonResponse(result, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            optional_org_param,
            AutoSchemaHelper.query_enum_field(
                "inventory_type", "Only return filter groups of this inventory type", INVENTORY_TYPES, required=False
            ),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Page number", default=1),
            OpenApiParameter("per_page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="Number of results per page", default=1000),
        ],
        responses={
            200: FilterGroupResponseSerializer(many=True),
            400: OpenApiResponse(description="Invalid inventory_type"),
        },
    )
    def list(self, request):
        page = request.query_params.get("page", 1)
        per_page = request.query_params.get("per_page", 1000)
        org_id = self.get_organization(request)

        filter_groups = FilterGroup.objects.filter(organization_id=org_id).prefetch_related(
            Prefetch("and_labels", queryset=StatusLabel.objects.only("id")),
            Prefetch("or_labels", queryset=StatusLabel.objects.only("id")),
            Prefetch("exclude_labels", queryset=StatusLabel.objects.only("id")),
        )

        if "inventory_type" in request.query_params:
            inventory_type = request.query_params.get("inventory_type")

            try:
                inventory_type_int = _get_inventory_type_int(inventory_type)
            except StopIteration:
                return JsonResponse(
                    {"success": False, "message": 'invalid "inventory_type" must be "Property" or "Tax Lot"'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                filter_groups = filter_groups.filter(inventory_type=inventory_type_int)

        paginator = Paginator(filter_groups, per_page)
        try:
            filter_groups = paginator.page(page).object_list
            page = int(page)
        except PageNotAnInteger:
            filter_groups = paginator.page(1).object_list
            page = 1
        except EmptyPage:
            filter_groups = paginator.page(paginator.num_pages).object_list
            page = paginator.num_pages

        return JsonResponse(
            {
                "status": "success",
                "pagination": {
                    "page": page,
                    "start": paginator.page(page).start_index(),
                    "end": paginator.page(page).end_index(),
                    "num_pages": paginator.num_pages,
                    "has_next": paginator.page(page).has_next(),
                    "has_previous": paginator.page(page).has_previous(),
                    "total": paginator.count,
                },
                "data": FilterGroupSerializer(filter_groups, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    def _get_labels(self, label_ids):
        """Split label_ids into the IDs of the organization's labels and the others"""
        organization = Organization.objects.get(pk=self.get_organization(self.request))
        org_labels = StatusLabel.objects.filter(super_organization=organization.get_parent())
        good_label_ids = []
        bad_label_ids = []
        for id in label_ids:
            label = org_labels.filter(id=id)

            if label.exists():
                good_label_ids.append(id)
            else:
                bad_label_ids.append(id)

        return good_label_ids, bad_label_ids
