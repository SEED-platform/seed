"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models import Property as PropertyModel
from seed.serializers.properties import CreatePropertySerializer, PropertyMinimalSerializer, PropertySerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


@extend_schema_org_query_param
@extend_schema_view(list=extend_schema(responses=PropertyMinimalSerializer))
@method_decorator(
    [
        has_perm("requires_viewer"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_id_kwarg="pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_id_kwarg="pk"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_id_kwarg="pk"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_member"),
    ],
    name="create",
)
class GBRPropertyViewSet(SEEDOrgCreateUpdateModelViewSet):
    """Properties API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': Property primary key,
                        'parent_property': id of associated parent property
                    }
                ]
            }


    retrieve:
        Return a Property instance by pk if it is within specified org.

    list:
        Return all Properties available to user through specified org.

    create:
        Create a new Property within user`s specified org.

    delete:
        Remove an existing Property.

    update:
        Update a Property record.

    partial_update:
        Update one or more fields on an existing Property.
    """

    def get_queryset(self):
        if hasattr(self.request, "access_level_instance_id"):
            access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

            return PropertyModel.objects.filter(
                organization_id=access_level_instance.organization_id,
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt,
            )

        else:
            return PropertyModel.objects.none()

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"access_level_instance_id": "integer"},
            description="`access_level_instance_id` is required unless the organization has only a root access level instance",
        ),
        responses={
            201: AutoSchemaHelper.schema_factory(
                {
                    "success": "boolean",
                    "message": {
                        "id": "integer",
                        "organization_id": "integer",
                        "access_level_instance_id": "integer",
                        "created": "datetime",
                        "updated": "datetime",
                        "inventory_documents": ["object"],
                    },
                },
                description="The created property is returned in `message` (`success` is always false)",
            ),
            400: OpenApiResponse(description="`access_level_instance_id` is required for this organization"),
            403: OpenApiResponse(description="The access level instance is not in the organization or not accessible to the user"),
        },
    )
    def create(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)
        access_level_instance_id = request.data.get("access_level_instance_id", None)

        # if no access_level_instance_id
        # if org only has root, just assign it to root
        # else error
        if access_level_instance_id is None:
            if AccessLevelInstance.objects.filter(organization_id=org_id).count() <= 1:
                org = Organization.objects.get(id=org_id)
                access_level_instance_id = org.root.id

            else:
                return JsonResponse({"success": False, "message": "requires access_level_instance"}, status=status.HTTP_400_BAD_REQUEST)

        # if the ali isn't in the org, or user does not have permissions to it, error
        try:
            property_ali = AccessLevelInstance.objects.get(pk=access_level_instance_id, organization_id=org_id)
        except (AccessLevelInstance.DoesNotExist, TypeError, ValueError):
            property_ali = None
        user_ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        if property_ali is None or not (user_ali == property_ali or property_ali.is_descendant_of(user_ali)):
            return JsonResponse({"success": False, "message": "no access to this access_level_instance"}, status=status.HTTP_403_FORBIDDEN)

        # save property
        property_serializer = CreatePropertySerializer(
            data={"organization_id": org_id, "access_level_instance_id": access_level_instance_id}
        )
        property_serializer.is_valid()
        property_serializer.save()

        return JsonResponse({"success": False, "message": property_serializer.data}, status=status.HTTP_201_CREATED)

    serializer_class = PropertySerializer
    model = PropertyModel
    data_name = "properties"
