"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from copy import deepcopy

import django.core.exceptions
from django.db import IntegrityError
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models import StatusLabel as Label
from seed.models.columns import Column
from seed.models.statistics_setups import StatisticsSetup
from seed.serializers.statistics_setups import StatisticsSetupSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.encrypt import decrypt, encrypt


def _validate_data(data, org_id):
    error = False
    msgs = []

    #  Validate Columns
    column_names = ["gfa_column", "electricity_column", "natural_gas_column"]
    for item in column_names:
        c_id = data.get(item)
        if c_id:
            c_col = Column.objects.get(pk=c_id)

            if c_col.organization_id != org_id:
                # error, this column does not belong to this org
                error = True
                msgs.append("The selected column for " + item + " does not belong to this organization")

    return error, msgs


class StastisticsSetupViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = StatisticsSetupSerializer
    model = StatisticsSetup

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def list(self, request):
        organization_id = self.get_organization(request)
        stats = StatisticsSetup.objects.filter(organization=organization_id)

        s_data = StatisticsSetupSerializer(stats, many=True).data

        return JsonResponse({"status": "success", "statistics": s_data}, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def retrieve(self, request, pk=0):
        organization = self.get_organization(request)
        if pk == 0:
            try:
                return JsonResponse(
                    {
                        "status": "success",
                        "statistic": StatisticsSetupSerializer(
                            StatisticsSetup.objects.filter(organization=organization).first()
                        ).data,
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception:
                return JsonResponse(
                    {"status": "error", "message": "No statistics setup exist with this identifier"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                data = StatisticsSetupSerializer(StatisticsSetup.objects.get(id=pk, organization=organization)).data
                return JsonResponse({"status": "success", "stastic": data}, status=status.HTTP_200_OK)
            except StatisticsSetup.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": f"Statistics Setup with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
                )

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            StatisticsSetup.objects.get(id=pk, organization=organization_id).delete()
        except StatisticsSetup.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Statistics with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        return JsonResponse({"status": "success", "message": f"Successfully deleted Statistics ID {pk}"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "gfa_column": "integer",
                "gfa_units": "string",
                "electricity_column": "integer",
                "electricity_units" : "string",
                "natural_gas_column": "integer",
                "natural_gas_units": "string"
            },
        ),
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def create(self, request):
        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "bad organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        data = deepcopy(request.data)
        data.update({"organization_id": org_id})

        error, msgs = _validate_data(data, org_id)
        if error is True:
            return JsonResponse({"status": "error", "message": ",".join(msgs)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StatisticsSetupSerializer(data=data)

        if not serializer.is_valid():
            error_response = {"status": "error", "message": "Data Validation Error", "errors": serializer.errors}
            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()

            return JsonResponse({"status": "success", "statistic": serializer.data}, status=status.HTTP_200_OK)
        except IntegrityError:
            return JsonResponse(
                {"status": "error", "message": "Only one statistics setup can be created per organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            return JsonResponse({"status": "error", "message": "Bad Request", "errors": message_dict}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "gfa_column": "integer",
                "gfa_units": "string",
                "electricity_column": "integer",
                "electricity_units": "string",
                "natural_gas_column": "integer",
                "natural_gas_units": "string"
            },
        ),
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def update(self, request, pk):
        org_id = self.get_organization(request)

        statistic = None
        try:
            statistic = StatisticsSetup.objects.get(id=pk, organization=org_id)
        except StatisticsSetup.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Statistics with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        data = deepcopy(request.data)
        error, msgs = _validate_data(data, org_id)
        if error is True:
            return JsonResponse({"status": "error", "message": ",".join(msgs)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StatisticsSetupSerializer(statistic, data=data, partial=True)

        if not serializer.is_valid():
            return JsonResponse(
                {"status": "error", "message": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "statistic": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            # rename key __all__ to general to make it more user-friendly
            if "__all__" in message_dict:
                message_dict["general"] = message_dict.pop("__all__")

            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": message_dict,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
