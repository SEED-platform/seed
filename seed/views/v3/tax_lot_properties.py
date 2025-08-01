"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from random import randint

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import AccessLevelInstance, Column, DerivedColumn, PropertyView, TaxLotProperty, TaxLotView
from seed.serializers.tax_lot_properties import TaxLotPropertySerializer
from seed.tasks import export_data_task, set_update_to_now
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.match import update_sub_progress_total

_log = logging.getLogger(__name__)

INVENTORY_MODELS = {"properties": PropertyView, "taxlots": TaxLotView}


class TaxLotPropertyViewSet(GenericViewSet, OrgMixin):
    """
    The TaxLotProperty field is used to return the properties and tax lots from the join table.
    This method presently only works with the CSV, but should eventually be extended to be the
    viewset for any tax lot / property join API call.
    """

    # For the Swagger page, GenericViewSet asserts a value exists for `queryset`
    queryset = TaxLotProperty.objects.none()
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotPropertySerializer

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_string_field("inventory_type", False, "Either 'taxlots' or 'properties' and defaults to 'properties'."),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "ids": ["integer"],
                "filename": "string",
                "export_type": "string",
                "profile_id": "integer",
                "progress_key": "string",
                "include_notes": "boolean",
                "include_meter_readings": "boolean",
            },
            description="- ids: (View) IDs for records to be exported\n"
            "- filename: desired filename including extension (defaulting to 'ExportedData.{export_type}')\n"
            "- export_types: 'csv', 'geojson', 'xlsx' (defaulting to 'csv')\n"
            "- profile_id: Column List Profile ID to use for customizing fields included in export"
            "- progress_key: (Optional) Used to find and update the ProgressData object. If none is provided, a ProgressData object will be created."
            "- include_notes: (Optional) Include notes in the export. Defaults to False."
            "- include_meter_readings: (Optional) Include notes in the export. Defaults to False.",
        ),
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def export(self, request):
        """
        Download a collection of the TaxLot and Properties in multiple formats via a background task.
        """
        org_id = request.query_params.get("organization_id")
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        ali_lft = access_level_instance.lft
        ali_rgt = access_level_instance.rgt
        request_data = request.data
        query_params = request.query_params

        progress_data = ProgressData(func_name="export_inventory", unique_id=f"{org_id}{randint(10000, 99999)}")
        progress_key = progress_data.key
        progress_data = update_sub_progress_total(100, progress_key)

        args = {
            "ali_lft": ali_lft,
            "ali_rgt": ali_rgt,
            "request_data": request_data,
            "org_id": org_id,
            "progress_key": progress_key,
            "query_params": query_params,
        }

        export_data_task.s(args).apply_async()

        return progress_data.result()

    def _serialized_coordinates(self, polygon_wkt):
        string_coord_pairs = polygon_wkt.lstrip("POLYGON (").rstrip(")").split(", ")

        coordinates = []
        for coord_pair in string_coord_pairs:
            float_coords = [float(coord) for coord in coord_pair.split(" ")]
            coordinates.append(float_coords)

        return coordinates

    def _serialized_point(self, point_wkt):
        string_coords = point_wkt.lstrip("POINT (").rstrip(")").split(", ")

        coordinates = []
        for coord in string_coords[0].split(" "):
            coordinates.append(float(coord))

        return coordinates

    def _extract_related(self, data):
        # extract all related records into a separate array
        related = []

        # figure out if we are dealing with properties or taxlots
        if data[0].get("property_state_id", None) is not None:
            is_property = True
        elif data[0].get("taxlot_state_id", None) is not None:
            is_property = False
        else:
            return []

        for datum in data:
            if datum.get("related", None) is not None:
                for record in datum["related"]:
                    related.append(record)

        # make array unique
        if is_property:
            unique = [dict(p) for p in {tuple(i.items()) for i in related}]
        else:
            unique = [dict(p) for p in {tuple(i.items()) for i in related}]

        return unique

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def start_set_update_to_now(self, request):
        """
        Generate a ProgressData object that will be used to monitor the set "update" of selected
        properties and tax lots to now
        """
        progress_data = ProgressData(func_name="set_update_to_now", unique_id=f"metadata{randint(10000, 99999)}")
        return progress_data.result()

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def set_update_to_now(self, request):
        """
        Kick off celery task to set "update" of selected inventory to now
        """
        property_view_ids = request.data.get("property_views")
        taxlot_view_ids = request.data.get("taxlot_views")
        progress_key = request.data.get("progress_key")

        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        property_view_ids = list(
            PropertyView.objects.filter(
                id__in=property_view_ids,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            ).values_list("id", flat=True)
        )
        taxlot_view_ids = list(
            TaxLotView.objects.filter(
                taxlot__access_level_instance__lft__gte=access_level_instance.lft,
                taxlot__access_level_instance__rgt__lte=access_level_instance.rgt,
                id__in=taxlot_view_ids,
            ).values_list("id", flat=True)
        )

        set_update_to_now.subtask([property_view_ids, taxlot_view_ids, progress_key]).apply_async()

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def update_derived_data(self, request):
        from seed.tasks import update_state_derived_data

        # get states
        org_id = self.get_organization(request)
        ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        taxlot_view_ids = request.data.get("taxlot_view_ids", [])
        taxlot_views = TaxLotView.objects.filter(
            id__in=taxlot_view_ids,
            cycle__organization_id=org_id,
            taxlot__access_level_instance__lft__gte=ali.lft,
            taxlot__access_level_instance__rgt__lte=ali.rgt,
        )
        taxlot_state_ids = list(taxlot_views.values_list("state", flat=True))

        property_view_ids = request.data.get("property_view_ids", [])
        property_views = PropertyView.objects.filter(
            id__in=property_view_ids,
            cycle__organization_id=org_id,
            property__access_level_instance__lft__gte=ali.lft,
            property__access_level_instance__rgt__lte=ali.rgt,
        )
        property_state_ids = list(property_views.values_list("state", flat=True))

        # get all derived_columns and set them to updating
        derived_columns = DerivedColumn.objects.filter(organization_id=org_id)
        Column.objects.filter(derived_column__in=derived_columns).update(is_updating=True)
        derived_column_ids = list(derived_columns.values_list("id", flat=True))

        # update
        result = update_state_derived_data(
            property_state_ids=property_state_ids, taxlot_state_ids=taxlot_state_ids, derived_column_ids=derived_column_ids
        )

        return JsonResponse(result)
