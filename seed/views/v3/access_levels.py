# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper

_log = logging.getLogger(__name__)


class AccessLevelViewSet(viewsets.ViewSet):
    @api_endpoint_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['GET'])
    def tree(self, request, organization_pk=None):
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        return Response({
            "access_level_names": org.access_level_names,
            "access_level_tree": AccessLevelInstance.dump_bulk(user_ali),
        },
            status=status.HTTP_200_OK,
        )

    @api_endpoint_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['POST'])
    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'parent_id': ['integer'],
                'name': ['string'],
            },
            required=['parent_id', 'name'],
            description='''
                - parent_id: id of the parent AccessLevelInstance
                - name: name of new level
            ''')
    )
    def add_instance(self, request, organization_pk=None):
        """Add an AccessLevelInstance to the tree
        """
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        # get and validate parent_id
        try:
            parent_id = request.data["parent_id"]
            assert isinstance(parent_id, int)
            parent = AccessLevelInstance.objects.get(pk=parent_id)
        except KeyError:
            return JsonResponse({
                'status': 'error',
                'message': 'body param `parent_id` is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        except AssertionError:
            return JsonResponse({
                'status': 'error',
                'message': 'body param `parent_id` must be int'
            }, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'AccessLevelInstance with `parent_id` {parent_id} does not exist.'
            }, status=status.HTTP_400_BAD_REQUEST)

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        if not (user_ali == parent or parent.is_descendant_of(user_ali)):
            return JsonResponse({
                'status': 'error',
                'message': f'AccessLevelInstance with `parent_id` {parent_id} does not exist.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # get and validate name
        try:
            name = request.data["name"]
            assert isinstance(name, str)
        except KeyError:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `name` is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        except AssertionError:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `name` must be str'
            }, status=status.HTTP_400_BAD_REQUEST)

        # assert access_level_names is long enough for the new node
        if parent.depth > len(org.access_level_names):
            return JsonResponse({
                'status': 'error',
                'message': 'orgs `access_level_names` is not long enough'
            }, status=status.HTTP_400_BAD_REQUEST)

        # create
        org.add_new_access_level_instance(parent_id, name)
        result = {
            "access_level_names": org.access_level_names,
            "access_level_tree": org.get_access_tree(),
        }

        status_code = status.HTTP_201_CREATED
        return JsonResponse(result, status=status_code)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['POST'])
    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'access_level_names': ['string']
            },
            required=['access_level_names'],
            description='A list of level names')
    )
    def access_level_names(self, request, organization_pk=None):
        """alter access_level names"""
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        # assert access_level_names list of str
        new_access_level_names = request.data.get('access_level_names')
        if new_access_level_names is None:
            return JsonResponse({
                'status': 'error',
                'message': 'body param `access_level_names` is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(new_access_level_names, list) or any([not isinstance(n, str) for n in new_access_level_names]):
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `access_level_names` must be a list of strings'
            }, status=status.HTTP_400_BAD_REQUEST)

        # assert access_level_names is deep enough
        depth = AccessLevelInstance.objects.filter(organization=org).aggregate(Max('depth')).get("depth__max", 0)
        if len(new_access_level_names) < depth:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `access_level_names` is shorter than depth of existing tree'
            }, status=status.HTTP_400_BAD_REQUEST)

        # save names
        org.access_level_names = new_access_level_names
        org.save()

        return org.access_level_names
