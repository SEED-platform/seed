"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
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
            ),
            400: OpenApiResponse(description="Missing or invalid IDs, or the property already has a view in the cycle"),
            404: OpenApiResponse(description="Property, cycle, or state not found in the organization or the user's access level"),
        },
    )
    def create(self, request, *args, **kwargs):
        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "bad organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Each ID must be an integer: has_hierarchy_access checks a property view from the query string instead of a
        # missing property_id, and int() would read a JSON `true` as 1
        try:
            ids = [request.data[key] for key in ("property_id", "cycle_id", "state_id")]
            if any(isinstance(value, bool) for value in ids):
                raise TypeError
            property_id, cycle_id, state_id = (int(value) for value in ids)
        except (KeyError, TypeError, ValueError, OverflowError):
            return JsonResponse(
                {"status": "error", "message": "property_id, cycle_id, and state_id must be integers"}, status=status.HTTP_400_BAD_REQUEST
            )

        duplicate_message = "The property already has a view in this cycle."
        try:
            # Lock the state while checking the views that use it and creating the view, so that concurrent requests
            # can't both find it unused and attach it to different properties. Saving the view also saves its property,
            # which can fail validation after the insert, which is then rolled back.
            with transaction.atomic():
                state = PropertyState.objects.select_for_update().filter(pk=state_id, organization_id=org_id).first()
                # The property is checked by has_hierarchy_access; the cycle and state must also be in the organization,
                # and a state already used by other property views must only be shared from views within the user's
                # access level. A state without a view (e.g., an import's, or a merged-away or edited record's) has no
                # access level instance to check, so only users of the root access level instance, who can access the
                # whole organization, may use it.
                state_views = PropertyView.objects.filter(state_id=state_id)
                if (
                    state is None
                    or not Cycle.objects.filter(pk=cycle_id, organization_id=org_id).exists()
                    or state_views.exclude(pk__in=self.get_queryset()).exists()
                    or (not state_views.exists() and not AccessLevelInstance.objects.get(pk=request.access_level_instance_id).is_root())
                ):
                    return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

                # A state may only be shared by views of the same property, which share its access level instance.
                # Otherwise users of one property's access level instance could edit (in place) or delete (deleting a
                # view's state deletes all of its views) another's view, e.g., an ancestor sharing a state between
                # sibling access levels.
                if state_views.exclude(property_id=property_id).exists():
                    return JsonResponse(
                        {"status": "error", "message": "The state belongs to another property's view."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if PropertyView.objects.filter(property_id=property_id, cycle_id=cycle_id).exists():
                    return JsonResponse({"status": "error", "message": duplicate_message}, status=status.HTTP_400_BAD_REQUEST)

                new_view = PropertyView.objects.create(property_id=property_id, cycle_id=cycle_id, state_id=state_id)
        except IntegrityError:
            # e.g., a concurrent request created a view of the property in the cycle with another state
            return JsonResponse({"status": "error", "message": duplicate_message}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "status": "success",
                "property_view": BriefPropertyViewSerializer(new_view).data,
            },
            status=status.HTTP_201_CREATED,
        )
