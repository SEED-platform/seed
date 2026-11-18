"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from copy import deepcopy

import django.core.exceptions
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models.compliance_metrics import ComplianceMetric
from seed.serializers.compliance_metrics import ComplianceMetricSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

compliance_metric_id_field = AutoSchemaHelper.path_id_field("Compliance metric ID")
COMPLIANCE_METRIC_BODY = {
    "name": "string",
    "cycles": ["integer"],
    "actual_energy_column": "integer",
    "target_energy_column": "integer",
    "energy_metric_type": ComplianceMetric.METRIC_TYPES,
    "actual_emission_column": "integer",
    "target_emission_column": "integer",
    "emission_metric_type": ComplianceMetric.METRIC_TYPES,
    "filter_group": "integer",
    "x_axis_columns": ["integer"],
}
compliance_metric_response = inline_serializer(
    "ComplianceMetricResponse", fields={"status": serializers.CharField(), "compliance_metric": ComplianceMetricSerializer()}
)


# the list action's response is a single envelope object, not an array
@extend_schema_serializer(many=False)
class ComplianceMetricListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    compliance_metrics = ComplianceMetricSerializer(many=True)


class ComplianceMetricViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = ComplianceMetricSerializer
    model = ComplianceMetric

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: ComplianceMetricListResponseSerializer},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def list(self, request):
        organization_id = self.get_organization(request)
        compliance_metric_queryset = ComplianceMetric.objects.filter(organization=organization_id)

        return JsonResponse(
            {"status": "success", "compliance_metrics": ComplianceMetricSerializer(compliance_metric_queryset, many=True).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[compliance_metric_id_field, AutoSchemaHelper.query_org_id_field()],
        responses={200: compliance_metric_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def retrieve(self, request, pk=0):
        organization = self.get_organization(request)
        if pk == 0:
            try:
                return JsonResponse(
                    {
                        "status": "success",
                        "compliance_metric": ComplianceMetricSerializer(
                            ComplianceMetric.objects.filter(organization=organization).first()
                        ).data,
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception:
                return JsonResponse({"status": "error", "message": "No Programs exist"}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                return JsonResponse(
                    {
                        "status": "success",
                        "compliance_metric": ComplianceMetricSerializer(
                            ComplianceMetric.objects.get(id=pk, organization=organization)
                        ).data,
                    },
                    status=status.HTTP_200_OK,
                )
            except ComplianceMetric.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": f"ComplianceMetric with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
                )

    @extend_schema(
        parameters=[compliance_metric_id_field, AutoSchemaHelper.query_org_id_field()],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "message": "string"})},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            ComplianceMetric.objects.get(id=pk, organization=organization_id).delete()
        except ComplianceMetric.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"ComplianceMetric with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        return JsonResponse({"status": "success", "message": f"Successfully deleted ComplianceMetric ID {pk}"}, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(COMPLIANCE_METRIC_BODY, required=["name"]),
        responses={200: compliance_metric_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def create(self, request):
        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "bad organization_id"}, status=status.HTTP_400_BAD_REQUEST)

        data = deepcopy(request.data)
        data.update({"organization_id": org_id})
        serializer = ComplianceMetricSerializer(data=data)

        if not serializer.is_valid():
            error_response = {"status": "error", "message": "Data Validation Error", "errors": serializer.errors}

            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({"status": "success", "compliance_metric": serializer.data}, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            return JsonResponse({"status": "error", "message": "Bad Request", "errors": message_dict}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[compliance_metric_id_field, AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(COMPLIANCE_METRIC_BODY),
        responses={200: compliance_metric_response},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk):
        org_id = self.get_organization(request)

        compliance_metric = None
        try:
            compliance_metric = ComplianceMetric.objects.get(id=pk, organization=org_id)
        except ComplianceMetric.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"ComplianceMetric with id {pk} does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        data = deepcopy(request.data)
        data.update({"organization_id": org_id})
        serializer = ComplianceMetricSerializer(compliance_metric, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse(
                {"status": "error", "message": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()
            return JsonResponse(
                {
                    "status": "success",
                    "compliance_metric": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
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

    @extend_schema(
        parameters=[
            compliance_metric_id_field,
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                "access_level_instance_id",
                required=False,
                description="Access level instance to evaluate (default: your own); must be within your access level",
            ),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "data": {
                        "meta": {"organization": "integer", "compliance_metric": "integer"},
                        "name": "string",
                        "graph_data": {"labels": ["string"], "datasets": ["object"]},
                        "cycles": [{"id": "integer", "name": "string"}],
                        "results_by_cycles": "object",
                        "properties_by_cycles": "object",
                        "metric": "object",
                    },
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
    @action(detail=True, methods=["GET"])
    def evaluate(self, request, pk):
        """
        Evaluate the compliance of the metric's properties, per cycle, within the given access level instance.
        """
        organization = self.get_organization(request)
        deepcopy(request.data)

        user_ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        requested_ali_id = request.query_params.get("access_level_instance_id")
        if requested_ali_id:
            try:
                requested_ali = AccessLevelInstance.objects.get(pk=requested_ali_id)
            except (AccessLevelInstance.DoesNotExist, ValueError):
                requested_ali = None
            if requested_ali is None or not (user_ali == requested_ali or requested_ali.is_descendant_of(user_ali)):
                return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)
        else:
            requested_ali = user_ali

        try:
            compliance_metric = ComplianceMetric.objects.get(id=pk, organization=organization)
        except Exception:
            return JsonResponse({"status": "error", "message": "ComplianceMetric does not exist"}, status=status.HTTP_404_NOT_FOUND)

        response = compliance_metric.evaluate(requested_ali)

        return JsonResponse({"status": "success", "data": response})
