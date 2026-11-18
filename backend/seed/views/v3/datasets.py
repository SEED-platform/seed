"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_field, extend_schema_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from seed.data_importer.models import ImportRecord
from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization, OrganizationUser
from seed.models import obj_to_dict
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.time_utils import convert_to_js_timestamp

_log = logging.getLogger(__name__)

# A dataset (ImportRecord) serialized by `obj_to_dict`, which includes all of its model fields
DATASET_FIELDS = {
    "id": "integer",
    "name": "string",
    "super_organization": "integer",
    "access_level_instance": "integer",
    "owner": "integer",
    "last_modified_by": "string",
    "created_at": "datetime",
    "updated_at": "integer",
}
SUCCESS_SCHEMA = AutoSchemaHelper.schema_factory({"status": "string"})


@extend_schema_field(
    AutoSchemaHelper.schema_factory(
        [{**DATASET_FIELDS, "importfiles": ["object"]}],
        description="`updated_at` is a JavaScript timestamp (ms) and `last_modified_by` is the user's email",
    )
)
class DatasetsField(serializers.JSONField):
    pass


# Schema only: the list action's response is a single envelope object, not an array
@extend_schema_serializer(many=False)
class DatasetListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    datasets = DatasetsField()


class DatasetViewSet(viewsets.ViewSet, OrgMixin):
    raise_exception = True

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: DatasetListResponseSerializer},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("can_view_data"),
        ]
    )
    def list(self, request):
        """
        Retrieves all datasets for the user's organization.
        """

        org_id = self.get_organization(request)
        org = Organization.objects.get(pk=org_id)
        datasets = []
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        import_records = ImportRecord.objects.filter(
            super_organization=org,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        )
        for d in import_records:
            importfiles = [obj_to_dict(f) for f in d.files]
            dataset = obj_to_dict(d)
            dataset["importfiles"] = importfiles
            if d.last_modified_by:
                dataset["last_modified_by"] = d.last_modified_by.email
            dataset["updated_at"] = convert_to_js_timestamp(d.updated_at)
            datasets.append(dataset)

        return JsonResponse(
            {
                "status": "success",
                "datasets": datasets,
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("Dataset (ImportRecord) ID"), AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body({"dataset": "string"}, required=["dataset"], description="The new name for this dataset"),
        responses={200: SUCCESS_SCHEMA},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_record_id_kwarg="pk"),
        ]
    )
    def update(self, request, pk=None):
        """
        Updates the name of a dataset (ImportRecord).
        """

        organization_id = self.get_organization(request)
        if organization_id is None:
            return JsonResponse({"status": "error", "message": "Missing organization_id query parameter"})
        try:
            organization_id = int(organization_id)
        except ValueError:
            return JsonResponse({"status": "error", "message": "Bad (non-numeric) organization_id"})
        dataset_id = pk
        name = request.data["dataset"]

        # check if user has access to the dataset
        d = ImportRecord.objects.filter(super_organization_id=organization_id, pk=dataset_id)

        if not d.exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "user does not have permission to update dataset",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        d = d[0]
        d.name = name
        d.save()
        return JsonResponse(
            {
                "status": "success",
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("Dataset (ImportRecord) ID"), AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "dataset": {**DATASET_FIELDS, "importfiles": [{"name": "string"}]}},
                description="`updated_at` is a JavaScript timestamp (ms) and `last_modified_by` is the user's email",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_view_data"),
            has_hierarchy_access(import_record_id_kwarg="pk"),
        ]
    )
    def retrieve(self, request, pk=None):
        """
        Retrieves a dataset (ImportRecord).
        """

        organization_id = self.get_organization(request)
        if organization_id is None:
            return JsonResponse(
                {"status": "error", "message": "Missing organization_id query parameter"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            organization_id = int(organization_id)
        except ValueError:
            return JsonResponse({"status": "error", "message": "Bad (non-numeric) organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        valid_orgs = (
            OrganizationUser.objects.filter(user_id=request.user.id).values_list("organization_id", flat=True).order_by("organization_id")
        )
        if organization_id not in valid_orgs:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Cannot access datasets for this organization id",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # check if dataset exists
        try:
            d = ImportRecord.objects.get(pk=pk)
        except ImportRecord.DoesNotExist:
            return JsonResponse({"status": "error", "message": f"dataset with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if d.super_organization_id != organization_id:
            return JsonResponse(
                {"status": "error", "message": "Organization ID mismatch between dataset and organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dataset = obj_to_dict(d)
        importfiles = []
        for f in d.files:
            importfile = obj_to_dict(f)
            if not f.uploaded_filename:
                importfile["name"] = f.filename_only
            else:
                importfile["name"] = f.uploaded_filename
            importfiles.append(importfile)

        dataset["importfiles"] = importfiles
        if d.last_modified_by:
            dataset["last_modified_by"] = d.last_modified_by.email
        dataset["updated_at"] = convert_to_js_timestamp(d.updated_at)

        return JsonResponse(
            {
                "status": "success",
                "dataset": dataset,
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("Dataset (ImportRecord) ID"), AutoSchemaHelper.query_org_id_field()],
        responses={200: SUCCESS_SCHEMA},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_record_id_kwarg="pk"),
        ]
    )
    def destroy(self, request, pk=None):
        """
        Deletes a dataset (ImportRecord).
        """
        organization_id = int(self.get_organization(request))
        dataset_id = pk
        # check if user has access to the dataset
        d = ImportRecord.objects.filter(super_organization_id=organization_id, pk=dataset_id)
        if not d.exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "user does not have permission to deactivate dataset",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        d = d[0]
        d.delete()
        return JsonResponse({"status": "success"})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body({"name": "string"}, required=["name"], description="Name of the dataset to be created"),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "id": "integer",
                    "name": "string",
                }
            )
        },
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
        ]
    )
    def create(self, request):
        """
        Creates a new empty dataset (ImportRecord).
        """

        body = request.data
        org_id = int(self.get_organization(request))

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "organization_id not provided"}, status=status.HTTP_400_BAD_REQUEST)
        record = ImportRecord.objects.create(
            name=body["name"],
            app="seed",
            start_time=timezone.now(),
            created_at=timezone.now(),
            last_modified_by=request.user,
            super_organization=org,
            owner=request.user,
            access_level_instance_id=request.access_level_instance_id,
        )

        return JsonResponse({"status": "success", "id": record.pk, "name": record.name})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "datasets_count": "integer",
                }
            )
        },
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def count(self, request):
        """
        Retrieves the number of datasets for an org.
        """
        org_id = int(self.get_organization(request))

        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        datasets_count = ImportRecord.objects.filter(
            super_organization_id=org_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        ).count()
        return JsonResponse({"status": "success", "datasets_count": datasets_count})
