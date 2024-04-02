# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models import Property as PropertyModel
from seed.serializers.properties import (
    CreatePropertySerializer,
    PropertySerializer
)
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


@method_decorator(
    name='list',
    decorator=[has_perm_class('requires_viewer')]
)
@method_decorator(
    name='retrieve',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(property_id_kwarg="pk")]
)
@method_decorator(
    name='destroy',
    decorator=[has_perm_class('requires_member'), has_hierarchy_access(property_id_kwarg="pk")]
)
@method_decorator(
    name='update',
    decorator=[has_perm_class('requires_member'), has_hierarchy_access(property_id_kwarg="pk")]
)
@method_decorator(
    name='create',
    decorator=[has_perm_class('requires_member')]
)
class GBRPropertyViewSet(SEEDOrgCreateUpdateModelViewSet):
    """Properties API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': Property primary key,
                        'parent_property': dict of associated parent property
                        'labels': list of associated label ids
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
        if hasattr(self.request, 'access_level_instance_id'):
            access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

            return PropertyModel.objects.filter(
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt,
            )

        else:
            return PropertyModel.objects.filter(pk=-1)

    def create(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)
        access_level_instance_id = request.data.get('access_level_instance_id', None)

        # if no access_level_instance_id
        # if org only has root, just assign it to root
        # else error
        if access_level_instance_id is None:
            if AccessLevelInstance.objects.filter(organization_id=org_id).count() <= 1:
                org = Organization.objects.get(id=org_id)
                access_level_instance_id = org.root.id

            else:
                return JsonResponse({
                    'success': False,
                    'message': "requires access_level_instance"
                }, status=status.HTTP_400_BAD_REQUEST)

        # if user does not have permissions to ali, error
        property_ali = AccessLevelInstance.objects.get(pk=access_level_instance_id)
        user_ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        if not (user_ali == property_ali or property_ali.is_descendant_of(user_ali)):
            return JsonResponse({
                'success': False,
                'message': "no access to this access_level_instance"
            }, status=status.HTTP_403_FORBIDDEN)

        # save property
        property_serializer = CreatePropertySerializer(data={"organization_id": org_id, **request.data})
        property_serializer.is_valid()
        property_serializer.save()

        return JsonResponse({
            'success': False,
            'message': property_serializer.data
        }, status=status.HTTP_201_CREATED)

    serializer_class = PropertySerializer
    model = PropertyModel
    data_name = "properties"
