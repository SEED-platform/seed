# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
import os

import xlrd
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from seed.data_importer.models import ImportRecord
from seed.data_importer.tasks import \
    save_raw_access_level_instances_data as task_save_raw
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    AccessLevelInstance,
    Organization,
    OrganizationUser
)
from seed.models import Analysis, Property, PropertyState, TaxLot, TaxLotState
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.views.v3.uploads import get_upload_path

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

        access_level_tree = []
        curr = access_level_tree

        # nest each ancestor underneath each other.
        # remember, we shouldn't see our aunts.
        for a in user_ali.get_ancestors():
            curr.append({
                'id': a.pk,
                'data': {
                    'name': a.name,
                    'organization': org.id,
                    'path': a.path,
                },
                'children': [],
            })
            curr = curr[0]["children"]

        # once we get to ourselves, we can see the whole tree
        curr.extend(org.get_access_tree(from_ali=user_ali))

        return Response({
            "access_level_names": org.access_level_names,
            "access_level_tree": access_level_tree,
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
            "access_level_tree": org.get_access_tree(from_ali=org.root),  # root as requires owner.
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
        depth = AccessLevelInstance.objects.filter(organization=org).aggregate(max_depth=Max('depth')).get("max_depth", 0)
        if len(new_access_level_names) < depth:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `access_level_names` is shorter than depth of existing tree'
            }, status=status.HTTP_400_BAD_REQUEST)

        # save names
        org.access_level_names = new_access_level_names
        try:
            org.save()
        except ValueError as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        return org.access_level_names

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['PUT'], parser_classes=(MultiPartParser,))
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.upload_file_field(
                name='file',
                required=True,
                description='File to Upload'
            ),
        ]
    )
    def importer(self, request, organization_pk=None):
        """Import access_level instance names from file"""
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        # Fineuploader requires the field to be qqfile it appears.
        if 'qqfile' in request.data:
            the_file = request.data['qqfile']
        else:
            the_file = request.data['file']
        filename = the_file.name
        path = get_upload_path(filename)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        extension = the_file.name.split(".")[-1]
        if extension == "xlsx" or extension == "xls":
            workbook = xlrd.open_workbook(file_contents=the_file.read())
            all_sheets_empty = True
            headers = []
            for sheet_name in workbook.sheet_names():
                try:
                    sheet = workbook.sheet_by_name(sheet_name)
                    if sheet.nrows > 0:
                        all_sheets_empty = False
                        headers = [str(cell.value).strip() for cell in sheet.row(0)]
                        break
                except xlrd.biffh.XLRDError:
                    pass

            if all_sheets_empty:
                return JsonResponse({
                    'success': False,
                    'message': "Import File %s was empty" % the_file.name
                })

            # compare headers with access levels
            # we can accept if headers are a subset of access levels
            # but not the other way around
            wrong_headers = False
            # handle having the root level in file or not
            level_names = org.access_level_names.copy()
            if headers[0] != level_names[0]:
                level_names.pop(0)

            for idx, name in enumerate(headers):
                if level_names[idx] != name:
                    wrong_headers = True

            if wrong_headers:
                return JsonResponse({
                    'success': False,
                    'message': "Import File %s's headers did not match the access level names." % the_file.name
                })

        # save the file
        with open(path, 'wb+') as temp_file:
            for chunk in the_file.chunks():
                temp_file.write(chunk)

        return JsonResponse({'success': True, 'tempfile': temp_file.name})

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request_body=AutoSchemaHelper.schema_factory({'filename': 'string'})
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['POST'])
    def start_save_data(self, request, organization_pk=None):
        """
        Starts a background task to import raw data from an ImportFile
        into PropertyState objects as extra_data. If the cycle_id is set to
        year_ending then the cycle ID will be set to the year_ending column for each
        record in the uploaded file. Note that the year_ending flag is not yet enabled.
        """
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        filename = request.data.get('filename')
        if not filename:
            return JsonResponse({
                'status': 'error',
                'message': 'must pass filename to save the data'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(task_save_raw(filename, org.id))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['PATCH'])
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': ['string']
            },
            required=['name'],
            description='Edited access level instance name')
    )
    def edit_instance(self, request, organization_pk=None, pk=None):

        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve Access Level Instances at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name')
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'must pass name to edit the access level instance name'
            }, status=status.HTTP_400_BAD_REQUEST)

        instance.name = name
        instance.save()
        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['GET'])
    def can_delete_instance(self, request, organization_pk=None, pk=None):
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve Access Level Instances at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)

        reasons_not_to_delete = []

        # Related ImportRecords
        related_import_record_count = ImportRecord.objects.filter(
            super_organization=org,
            access_level_instance__lft__gte=instance.lft,
            access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_import_record_count > 0:
            reasons_not_to_delete.append(f"Has {related_import_record_count} related ImportRecords")

        # Related OrganizationUsers
        related_organization_user_count = OrganizationUser.objects.filter(
            organization=org,
            access_level_instance__lft__gte=instance.lft,
            access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_organization_user_count > 0:
            reasons_not_to_delete.append(f"Has {related_organization_user_count} related OrganizationUsers")

        # Related Analyses
        related_analysis_count = Analysis.objects.filter(
            organization=org,
            access_level_instance__lft__gte=instance.lft,
            access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_analysis_count > 0:
            reasons_not_to_delete.append(f"Has {related_analysis_count} related Analysis")

        # Related Properties
        related_property_count = Property.objects.filter(
            organization=org,
            access_level_instance__lft__gte=instance.lft,
            access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_property_count > 0:
            reasons_not_to_delete.append(f"Has {related_property_count} related properties")

        # Related PropertyStates
        related_property_state_count = PropertyState.objects.filter(
            organization=org,
            raw_access_level_instance__lft__gte=instance.lft,
            raw_access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_property_state_count > 0:
            reasons_not_to_delete.append(f"Has {related_property_state_count} related Property States")

        # Related Taxlots
        related_taxlot_count = TaxLot.objects.filter(
            organization=org,
            access_level_instance__lft__gte=instance.lft,
            access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_taxlot_count > 0:
            reasons_not_to_delete.append(f"Has {related_taxlot_count} related Taxlot")

        # Related TaxlotStates
        related_taxlot_state_count = TaxLotState.objects.filter(
            organization=org,
            raw_access_level_instance__lft__gte=instance.lft,
            raw_access_level_instance__rgt__lte=instance.rgt,
        ).count()
        if related_taxlot_state_count > 0:
            reasons_not_to_delete.append(f"Has {related_taxlot_state_count} related TaxlotState")

        if len(reasons_not_to_delete) == 0:
            return JsonResponse({
                'can_delete': True,
            }, status=status.HTTP_200_OK
            )

        else:
            return JsonResponse({
                'can_delete': False,
                "reasons": reasons_not_to_delete,
            }, status=status.HTTP_200_OK
            )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['DElETE'])
    def delete_instance(self, request, organization_pk=None, pk=None):
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve Access Level Instances at pk = ' + str(pk)},
                                status=status.HTTP_404_NOT_FOUND)
        # get instance
        if instance == org.root:
            return JsonResponse({'status': 'error',
                                 'message': 'Cannot delete root.'},
                                status=status.HTTP_400_BAD_REQUEST)

        instance.delete()

        return JsonResponse({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)
