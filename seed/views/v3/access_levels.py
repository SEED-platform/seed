"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import os
from pathlib import Path

import xlrd
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from seed.data_importer.models import ImportRecord
from seed.data_importer.tasks import save_raw_access_level_instances_data as task_save_raw
from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization, OrganizationUser
from seed.models import Analysis, Property, PropertyState, TaxLot, TaxLotState
from seed.serializers.access_level_instances import AccessLevelInstanceSerializer
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.views.v3.uploads import get_upload_path

_log = logging.getLogger(__name__)


def _uploads_subdir(org_id):
    """The directory, relative to the uploads directory, where `importer` saves the organization's files"""
    return os.path.join("access_levels", str(org_id))


def _is_uploaded_file(filename, org_id):
    """Whether `filename` is a path in the directory where `importer` saves the organization's files"""
    uploads_dir = Path(settings.MEDIA_ROOT, "uploads", _uploads_subdir(org_id)).resolve()
    try:
        return isinstance(filename, str) and Path(filename).resolve().is_relative_to(uploads_dir)
    except (OSError, ValueError):
        return False


ali_id_path_field = AutoSchemaHelper.path_id_field("Access Level Instance ID")

ali_fields = {"id": "integer", "name": "string", "organization": "integer", "path": "object"}

access_level_tree_schema = {
    "type": "object",
    "properties": {
        "access_level_names": AutoSchemaHelper.schema_factory(["string"]),
        "access_level_tree": {
            "type": "array",
            "items": AutoSchemaHelper.schema_factory(
                {**ali_fields, "children": ["object"]},
                description="An Access Level Instance; `path` maps level names to instance names, and `children` (omitted on leaves) "
                "holds nested instances of the same shape",
            ),
        },
    },
}


def _lock_access_level_tree(org):
    """Lock the organization's row until the end of the current transaction, so concurrent requests that add or
    rename access level instances run their sibling-name check and write one at a time"""
    Organization.objects.select_for_update().only("pk").get(pk=org.pk)


@extend_schema(parameters=[AutoSchemaHelper.path_id_field("Organization ID", name="organization_pk")])
class AccessLevelViewSet(viewsets.ViewSet):
    @extend_schema(responses={200: access_level_tree_schema})
    @method_decorator(
        [
            api_endpoint,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def tree(self, request, organization_pk=None):
        """
        Retrieve the Access Level Tree visible to the user: the ancestors and descendants of their Access Level Instance.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        access_level_tree = []
        curr = access_level_tree

        # nest each ancestor underneath each other.
        # remember, we shouldn't see our aunts.
        for a in AccessLevelInstance.objects.get_ancestors(user_ali):
            curr.append(
                {
                    "id": a.pk,
                    "name": a.name,
                    "organization": org.id,
                    "path": a.path,
                    "children": [],
                }
            )
            curr = curr[0]["children"]

        # once we get to ourselves, we can see the whole tree
        curr.extend(org.get_access_tree(from_ali=user_ali))

        return Response(
            {
                "access_level_names": org.access_level_names,
                "access_level_tree": access_level_tree,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: access_level_tree_schema})
    @method_decorator(
        [
            api_endpoint,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def descendant_tree(self, request, organization_pk=None):
        """
        Retrieve Access Level Tree data for a Access Level Instance and its descendants.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
            user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "No such resource."},
                status=status.HTTP_404_NOT_FOUND,
            )

        access_level_tree = org.get_access_tree(from_ali=user_ali)
        # find level names for current node and descendants
        descendants = AccessLevelInstance.objects.get_descendants(user_ali)
        if descendants:
            end_depth = max(descendant.get_depth() for descendant in descendants)
        else:
            end_depth = user_ali.get_depth()
        start_depth = user_ali.get_depth() - 1
        level_names = org.access_level_names[start_depth:end_depth]

        return Response(
            {
                "access_level_names": level_names,
                "access_level_tree": access_level_tree,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {
                "parent_id": "integer",
                "name": "string",
            },
            required=["parent_id", "name"],
            description="""
                - parent_id: id of the parent AccessLevelInstance
                - name: name of new level
            """,
        ),
        responses={201: access_level_tree_schema},
    )
    @method_decorator(
        [
            api_endpoint,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def add_instance(self, request, organization_pk=None):
        """Add an AccessLevelInstance to the tree"""
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get and validate parent_id
        try:
            parent_id = request.data["parent_id"]
            if not isinstance(parent_id, int):
                return JsonResponse(
                    {"status": "error", "message": "body param `parent_id` must be int"}, status=status.HTTP_400_BAD_REQUEST
                )
            parent = AccessLevelInstance.objects.get(pk=parent_id, organization=org)
        except KeyError:
            return JsonResponse({"status": "error", "message": "body param `parent_id` is required"}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"AccessLevelInstance with `parent_id` {parent_id} does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # get and validate name
        try:
            name = request.data["name"]
            if not isinstance(name, str):
                return JsonResponse({"status": "error", "message": "Query param `name` must be str"}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return JsonResponse({"status": "error", "message": "Query param `name` is required"}, status=status.HTTP_400_BAD_REQUEST)

        # assert access_level_names is long enough for the new node
        if parent.depth > len(org.access_level_names):
            return JsonResponse(
                {"status": "error", "message": "orgs `access_level_names` is not long enough"}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            _lock_access_level_tree(org)
            # re-read the parent under the lock: get_children() uses its nested-set bounds, which a request that just
            # added a child may have changed
            parent.refresh_from_db()

            # siblings share a hierarchical path, so their names must be unique
            if AccessLevelInstance.objects.get_children(parent).filter(organization=org, name=name).exists():
                return JsonResponse(
                    {"status": "error", "message": "An access level instance with this name already exists under this parent"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # create
            org.add_new_access_level_instance(parent_id, name)
        result = {
            "access_level_names": org.access_level_names,
            "access_level_tree": org.get_access_tree(from_ali=org.root),  # root as requires owner.
        }

        status_code = status.HTTP_201_CREATED
        return JsonResponse(result, status=status_code)

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"access_level_names": ["string"]}, required=["access_level_names"], description="A list of level names"
        ),
        responses={200: AutoSchemaHelper.schema_factory(["string"], description="The organization's updated access level names")},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def access_level_names(self, request, organization_pk=None):
        """alter access_level names"""
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        # assert access_level_names list of str
        new_access_level_names = request.data.get("access_level_names")
        if new_access_level_names is None:
            return JsonResponse(
                {"status": "error", "message": "body param `access_level_names` is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(new_access_level_names, list) or any(not isinstance(n, str) for n in new_access_level_names):
            return JsonResponse(
                {"status": "error", "message": "Query param `access_level_names` must be a list of strings"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_access_level_names) < 1:
            return JsonResponse(
                {"status": "error", "message": "There must be at least one access level."}, status=status.HTTP_400_BAD_REQUEST
            )
        if any(n == "" for n in new_access_level_names):
            return JsonResponse({"status": "error", "message": 'Access Level Instance may not be ""'}, status=status.HTTP_400_BAD_REQUEST)

        # delete alis at deleted depths and save the names together, so rejected names don't delete any alis
        depth = len(new_access_level_names)
        try:
            with transaction.atomic():
                # lock the tree before deleting in the same order as adding and renaming instances so they can't deadlock
                _lock_access_level_tree(org)
                org.refresh_from_db()
                AccessLevelInstance.objects.filter(organization=org, depth__gt=depth).delete()
                org.access_level_names = new_access_level_names
                org.save()
        except ValueError as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return org.access_level_names

    @extend_schema(
        request=AutoSchemaHelper.multipart_body(
            {"file": "file"}, required=["file"], description="Access Level Instances file to upload (`qqfile` is also accepted)"
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"success": "boolean", "tempfile": "string", "message": "string"},
                description="On success, `tempfile` is the uploaded file's server path to pass to `start_save_data`; "
                "otherwise `success` is false and `message` explains why",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=False, methods=["PUT"], parser_classes=(MultiPartParser,))
    def importer(self, request, organization_pk=None):
        """Import access_level instance names from file"""
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        if len(request.FILES) == 0:
            return JsonResponse({"success": False, "message": "Must pass file in as a Multipart/Form post"})

        # Fineuploader requires the field to be qqfile it appears.
        if "qqfile" in request.data:
            the_file = request.data["qqfile"]
        else:
            the_file = request.data["file"]
        filename = the_file.name
        path = get_upload_path(os.path.join(_uploads_subdir(org.id), filename))

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        extension = the_file.name.split(".")[-1]
        if extension in {"xls", "xlsx"}:
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
                return JsonResponse({"success": False, "message": f"Import File {the_file.name} was empty"})

            # compare headers with access levels
            # we can accept if headers are a subset of access levels
            # but not the other way around
            wrong_headers = False
            # handle having the root level in file or not
            level_names = org.access_level_names.copy()
            if headers[0] != level_names[0]:
                level_names.pop(0)

            for idx, name in enumerate(headers):
                if idx >= len(level_names):
                    wrong_headers = True
                    break
                if level_names[idx] != name:
                    wrong_headers = True
                    break

            if wrong_headers:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Import File {the_file.name}'s headers did not match the Access Level names defined in SEED. Click the 'Edit/Add Access Levels' button to review your defined access levels before uploading the file. ",
                    }
                )

        # save the file
        with open(path, "wb+") as temp_file:
            temp_file.writelines(the_file.chunks())

        return JsonResponse({"success": True, "tempfile": temp_file.name})

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"filename": "string"}, required=["filename"], description="- filename: the `tempfile` returned by `importer`"
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "status_message": "string",
                    "progress": "number",
                    "progress_key": "string",
                    "unique_id": "integer",
                    "func_name": "string",
                    "message": "string",
                    "stacktrace": "string",
                    "summary": "object",
                    "total": "integer",
                },
                description="Progress data of the background task",
            ),
            400: AutoSchemaHelper.schema_factory(
                {"status": "string", "message": "string"}, description="`filename` is missing or is not a file uploaded with `importer`"
            ),
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def start_save_data(self, request, organization_pk=None):
        """
        Starts a background task to create the Access Level Instances listed in a file uploaded with `importer`.
        """
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        filename = request.data.get("filename")
        if not filename:
            return JsonResponse({"status": "error", "message": "must pass filename to save the data"}, status=status.HTTP_400_BAD_REQUEST)
        if not _is_uploaded_file(filename, org.id):
            return JsonResponse(
                {"status": "error", "message": "filename must be the `tempfile` returned by `importer`"}, status=status.HTTP_400_BAD_REQUEST
            )

        return JsonResponse(task_save_raw(filename, org.id))

    @extend_schema(
        parameters=[ali_id_path_field],
        request=AutoSchemaHelper.json_body({"name": "string"}, required=["name"], description="Edited access level instance name"),
        responses={200: AutoSchemaHelper.schema_factory({"status": "string"})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def edit_instance(self, request, organization_pk=None, pk=None):
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve Access Level Instances at pk = " + str(pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        name = request.data.get("name")
        if not name:
            return JsonResponse(
                {"status": "error", "message": "must pass name to edit the access level instance name"}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            _lock_access_level_tree(org)
            # re-read the instance under the lock, so saving it can't write back a tree position changed meanwhile
            instance.refresh_from_db()

            # siblings share a hierarchical path, so their names must be unique. treebeard treats every organization's
            # root as a sibling of the others, so only compare instances in this organization
            if AccessLevelInstance.objects.get_siblings(instance).filter(organization=org, name=name).exclude(pk=instance.pk).exists():
                return JsonResponse(
                    {"status": "error", "message": "An access level instance with this name already exists under this parent"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            instance.name = name
            instance.save()
        return JsonResponse({"status": "success"})

    @extend_schema(
        parameters=[ali_id_path_field],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"can_delete": "boolean", "reasons": ["string"]},
                description="`reasons` lists the related records preventing deletion, and is only present when `can_delete` is false",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def can_delete_instance(self, request, organization_pk=None, pk=None):
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve Access Level Instances at pk = " + str(pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

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
            return JsonResponse(
                {
                    "can_delete": True,
                },
                status=status.HTTP_200_OK,
            )

        else:
            return JsonResponse(
                {
                    "can_delete": False,
                    "reasons": reasons_not_to_delete,
                },
                status=status.HTTP_200_OK,
            )

    @extend_schema(
        parameters=[ali_id_path_field],
        request=None,
        responses={204: OpenApiResponse(description="The Access Level Instance and its descendants were deleted")},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=True, methods=["DElETE"])
    def delete_instance(self, request, organization_pk=None, pk=None):
        # get org
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get instance
        try:
            instance = AccessLevelInstance.objects.filter(organization=org.pk).get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve Access Level Instances at pk = " + str(pk)},
                status=status.HTTP_404_NOT_FOUND,
            )
        # get instance
        if instance == org.root:
            return JsonResponse({"status": "error", "message": "Cannot delete root."}, status=status.HTTP_400_BAD_REQUEST)

        instance.delete()

        return JsonResponse({"status": "success"}, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"inventory_type": "integer", "inventory_ids": ["integer"]},
            description="""
                - inventory_type: 1 for tax lots; any other value for properties
                - inventory_ids: IDs of the properties or tax lots
            """,
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "data": AutoSchemaHelper.schema_factory(
                        {**ali_fields, "lft": "integer", "rgt": "integer", "tree_id": "integer", "depth": "integer"},
                        nullable=True,
                        description="The lowest common Access Level Instance, or null if no inventory was found",
                    ),
                },
            }
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def lowest_common_ancestor(self, request, organization_pk=None):
        """
        * THIS IS NOT IN USE, but could be useful in future development


        Given a list of inventory, find the least common ancestor between multiple properties within a group

        Example ALI tree:
             A
           /   \
          B     C
         /\
        D  E

        least common ancestor:
        if A and D -> A
        if B and C -> A
        if B and D -> B
        if D and E -> B
        """
        inventory_type = request.data.get("inventory_type")
        inventory_ids = request.data.get("inventory_ids")
        if not inventory_ids:
            return JsonResponse({"status": "success", "data": None})

        inventory_type, InventoryClass = ("taxlot", TaxLot) if inventory_type == 1 else ("property", Property)
        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        inventory = InventoryClass.objects.filter(
            id__in=inventory_ids,
            organization_id=organization_pk,
            access_level_instance__lft__gte=user_ali.lft,
            access_level_instance__rgt__lte=user_ali.rgt,
        )
        alis = [i.access_level_instance for i in list(inventory)]
        if not alis:
            return JsonResponse({"status": "success", "data": None})

        left_most = min([ali.lft for ali in alis])
        right_most = max([ali.lft for ali in alis])
        shared_ancestors = AccessLevelInstance.objects.filter(organization_id=organization_pk, lft__lte=left_most, rgt__gte=right_most)
        lowest_common = shared_ancestors.order_by("depth").last()

        serialized_ali = AccessLevelInstanceSerializer(lowest_common).data
        return JsonResponse({"status": "success", "data": serialized_ali})

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "inventory_type": {
                        "type": "string",
                        "enum": ["properties", "taxlots"],
                        "default": "properties",
                        "description": "Any value other than `taxlots` selects properties",
                    },
                    "view_ids": AutoSchemaHelper.schema_factory(["integer"], description="Property or tax lot view IDs"),
                },
            }
        },
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "access_level_instance_ids": ["integer"]},
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
    @action(detail=False, methods=["POST"])
    def filter_by_views(self, request, organization_pk=None):
        """
        Return a distinct list of access_level_instance_ids for a group of inventory_ids
        """
        inventory_type = request.data.get("inventory_type", 0)
        view_ids = request.data.get("view_ids")
        if not view_ids:
            return JsonResponse({"status": "success", "access_level_instance_ids": []})

        InventoryClass, ali_relation = (TaxLot, "taxlots") if inventory_type == "taxlots" else (Property, "properties")
        inventory_ids = InventoryClass.objects.filter(views__id__in=view_ids, organization_id=organization_pk).values_list("id", flat=True)
        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        access_level_instance_ids = (
            AccessLevelInstance.objects.filter(**{f"{ali_relation}__in": inventory_ids}, lft__gte=user_ali.lft, rgt__lte=user_ali.rgt)
            .distinct()
            .values_list("id", flat=True)
        )

        return JsonResponse({"status": "success", "access_level_instance_ids": list(access_level_instance_ids)})
