"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status

from seed.filtersets import PropertyViewFilterSet
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import AccessLevelInstance, Cycle, Organization, PropertyState, PropertyView
from seed.serializers.properties import BriefPropertyViewSerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgModelViewSet


@extend_schema_org_query_param
# BriefPropertyViewSerializer has no writable fields, so updates do not read a body
@extend_schema_view(update=extend_schema(request=None), partial_update=extend_schema(request=None))
@method_decorator(
    [
        has_perm("requires_viewer"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="pk"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="pk"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(body_property_id="property_id"),
    ],
    name="create",
)
class PropertyViewViewSet(SEEDOrgModelViewSet):
    """PropertyViews API Endpoint

        Returns::
            {
                'status': 'success',
                'property_views': [
                    {
                        'id': PropertyView primary key,
                        'property_id': id of associated Property,
                        'cycle': dict of associated Cycle values
                    }
                ]
            }


    retrieve:
        Return a PropertyView instance by pk if it is within specified org.

    list:
        Return all PropertyViews available to user through specified org.

    create:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Create a new PropertyView within user`s specified org.

    delete:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Remove an existing PropertyView.

    update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update a PropertyView record.

    partial_update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update one or more fields on an existing PropertyView.
    """

    def get_queryset(self):
        if hasattr(self.request, "access_level_instance_id"):
            access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

            return PropertyView.objects.filter(
                property__organization_id=access_level_instance.organization_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )

        else:
            return PropertyView.objects.none()

    serializer_class = BriefPropertyViewSerializer
    pagination_class = None
    model = PropertyView
    filterset_class = PropertyViewFilterSet
    orgfilter = "property__organization_id"
    data_name = "property_views"
    queryset = PropertyView.objects.all()

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"property_id": "integer", "cycle_id": "integer", "state_id": "integer"}, required=["property_id", "cycle_id", "state_id"]
        ),
        responses={
            201: AutoSchemaHelper.schema_factory(
                {"status": "string", "property_view": {"id": "integer", "cycle": "object", "property_id": "integer"}}
            )
        },
    )
    def create(self, request, *args, **kwargs):
        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "bad organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        # The property is checked by has_hierarchy_access; the cycle and state must also be in the organization, and a
        # state already used by other property views must only be shared from views within the user's access level
        cycle_id, state_id = request.data.get("cycle_id"), request.data.get("state_id")
        if (
            not Cycle.objects.filter(pk=cycle_id, organization_id=org_id).exists()
            or not PropertyState.objects.filter(pk=state_id, organization_id=org_id).exists()
            or PropertyView.objects.filter(state_id=state_id).exclude(pk__in=self.get_queryset()).exists()
        ):
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        try:
            new_view = PropertyView.objects.create(property_id=request.data.get("property_id"), cycle_id=cycle_id, state_id=state_id)
            new_view.save()
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "status": "success",
                "property_view": BriefPropertyViewSerializer(new_view).data,
            },
            status=status.HTTP_201_CREATED,
        )
