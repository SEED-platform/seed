"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from datetime import datetime
from random import randint

import xlrd
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone as django_timezone
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.data_importer.meters_parser import MetersParser
from seed.data_importer.models import ROW_DELIMITER, ImportRecord
from seed.data_importer.sensor_readings_parser import SensorsReadingsParser
from seed.data_importer.tasks import do_checks, geocode_and_match_buildings_task, map_data, mapping_results_task
from seed.data_importer.tasks import save_raw_data as task_save_raw
from seed.data_importer.tasks import validate_use_cases as task_validate_use_cases
from seed.data_importer.utils import kbtu_thermal_conversion_factors, kgal_water_conversion_factors
from seed.decorators import ajax_request
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mcm import mapper, reader
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, OrganizationUser
from seed.lib.xml_mapping import mapper as xml_mapper
from seed.models import (
    ASSESSED_RAW,
    AUDIT_USER_EDIT,
    DATA_STATE_MATCHING,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    PORTFOLIO_METER_USAGE,
    SEED_DATA_SOURCES,
    Column,
    Cycle,
    DataLogger,
    ImportFile,
    Meter,
    MeterReading,
    Organization,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    System,
    TaxLotAuditLog,
    TaxLotState,
    get_column_mapping,
    obj_to_dict,
)
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import PROGRESS_DATA_SCHEMA, AutoSchemaHelper
from seed.utils.import_file import verify_data_types
from seed.utils.time_utils import localize_datetime_with_dst_fallbacks

_log = logging.getLogger(__name__)


STATUS_MESSAGE_SCHEMA = AutoSchemaHelper.schema_factory({"status": "string", "message": "string"})
# Matching and geocoding counts for one inventory type
MATCHING_RESULTS_COUNTS = dict.fromkeys(
    [
        "initial_incoming",
        "duplicates_against_existing",
        "duplicates_within_file",
        "duplicates_within_file_errors",
        "merges_against_existing",
        "merges_against_existing_errors",
        "merges_between_existing",
        "merges_within_file",
        "merges_within_file_errors",
        "new",
        "new_errors",
        "geocoded_high_confidence",
        "geocoded_low_confidence",
        "geocoded_census_geocoder",
        "geocoded_manually",
        "geocode_not_possible",
    ],
    "integer",
)
# A meter (see `MetersParser.proposed_imports`) and the parsed type/unit combinations of a meter import preview
METER_PROPOSED_IMPORT = {"source_id": "string", "type": "string", "incoming": "integer", "property_id": "integer", "system_id": "integer"}
VALIDATED_TYPE_UNITS = [{"parsed_type": "string", "parsed_unit": "string"}]


def convert_first_five_rows_to_list(header, first_five_rows):
    """
    Return the first five rows. This is a complicated method because it handles converting the
    persisted format of the first five rows into a list of dictionaries. It handles some basic
    logic if there are crlf in the fields. Note that this method does not cover all the use cases
    and cannot due to the custom delimiter. See the tests in
    test_views.py:test_get_first_five_rows_newline_should_work to see the limitation

    :param header: list, ordered list of headers as strings
    :param first_five_rows: string, long string with |#*#| delimiter.
    :return: list
    """
    row_data = []
    rows = []
    number_of_columns = len(header)
    split_cells = first_five_rows.split(ROW_DELIMITER)
    number_cells = len(split_cells)
    # catch the case where there is only one column, therefore no ROW_DELIMITERs
    if number_of_columns == 1:
        # Note that this does not support having a single column with carriage returns!
        rows = [[row] for row in first_five_rows.splitlines()]
    else:
        for idx, line in enumerate(split_cells):
            crlf_count = line.count("\n")

            if crlf_count == 0:
                row_data.append(line)
            elif crlf_count >= 1:
                # if add this element to row_data equals number_of_columns, then it is a new row
                if len(row_data) == number_of_columns - 1:
                    # check if this is the last columns, if so, then just store the value and move on
                    if idx == number_cells - 1:
                        row_data.append(line)
                        rows.append(row_data)
                        continue
                    else:
                        # split the cell_data. The last cell becomes the beginning of the new
                        # row, and the other cells stay joined with \n.
                        cell_data = line.splitlines()
                        row_data.append("\n".join(cell_data[:crlf_count]))
                        rows.append(row_data)

                        # initialize the next row_data with the remainder
                        row_data = [cell_data[-1]]
                        continue
                else:
                    # this is not the end, so it must be a carriage return in the cell, just save data
                    row_data.append(line)

            if len(row_data) == number_of_columns:
                rows.append(row_data)

    return [dict(zip(header, row, strict=False)) for row in rows]


class ImportFileViewSet(viewsets.ViewSet, OrgMixin):
    raise_exception = True
    queryset = ImportFile.objects.all()

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "import_file": {
                        "id": "integer",
                        "name": "string",
                        "uploaded_filename": "string",
                        "source_type": "string",
                        "import_record": "integer",
                        "cycle": "integer",
                        "dataset": "object",
                    },
                },
                description="`import_file` contains all of the ImportFile's fields, and `dataset` all of its ImportRecord's fields",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    def retrieve(self, request, pk=None):
        """
        Retrieves details about an ImportFile.
        """
        import_file_id = pk
        orgs = request.user.orgs.all()
        try:
            import_file = ImportFile.objects.get(pk=import_file_id)
            d = ImportRecord.objects.filter(super_organization__in=orgs, pk=import_file.import_record_id)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not access an import file with this ID"}, status=status.HTTP_403_FORBIDDEN
            )
        # check if user has access to the import file
        if not d.exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Could not locate import file with this ID",
                    "import_file": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        f = obj_to_dict(import_file)
        f["name"] = import_file.filename_only
        if not import_file.uploaded_filename:
            f["uploaded_filename"] = import_file.filename
        f["dataset"] = obj_to_dict(import_file.import_record)

        return JsonResponse(
            {
                "status": "success",
                "import_file": f,
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "data": "boolean"})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def check_meters_tab_exists(self, request, pk=None):
        """
        Checks for the existence of meters tab "Meter Entries" for a file.
        """
        org_id = self.get_organization(request)
        try:
            import_file = ImportFile.objects.get(id=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            resp = {"status": "error", "message": "Could not find import file with pk=" + str(pk)}
            return JsonResponse(resp, status=status.HTTP_400_BAD_REQUEST)

        try:
            has_meter_tab = bool({"Meter Entries", "Monthly Usage"} & set(xlrd.open_workbook(import_file.file.path).sheet_names()))
            return JsonResponse({"status": "success", "data": has_meter_tab})
        except xlrd.XLRDError:
            return JsonResponse({"status": "success", "data": False})

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(required=False, description="Organization ID (may instead be sent in the request body)"),
        ],
        request=AutoSchemaHelper.json_body(
            {"import_file_id": "integer", "organization_id": "integer"},
            required=["import_file_id"],
            description="- import_file_id: ID of a mapped Assessed Raw ImportFile whose file also contains meter data",
        ),
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "import_file_id": "integer"})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(body_import_file_id="import_file_id"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def reuse_inventory_file_for_meters(self, request):
        org_id = self.get_organization(request)
        try:
            import_file_id = request.data.get("import_file_id", 0)
            original_file = ImportFile.objects.get(
                id=import_file_id,
                import_record__super_organization_id=org_id,
                mapping_done=True,
                source_type=SEED_DATA_SOURCES[ASSESSED_RAW][1],
            )
        except ImportFile.DoesNotExist:
            resp = {"status": "error", "message": "Could not find previously imported inventory file with pk=" + str(import_file_id)}
            return JsonResponse(resp, status=status.HTTP_400_BAD_REQUEST)

        new_file = ImportFile.objects.create(
            import_record=original_file.import_record,
            file=original_file.file,
            uploaded_filename=original_file.uploaded_filename,
            source_type=SEED_DATA_SOURCES[PORTFOLIO_METER_USAGE][1],
        )

        return JsonResponse({"status": "success", "import_file_id": new_file.id})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "first_five_rows": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                        "description": "Rows keyed by the file's column headers",
                    },
                },
            }
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def first_five_rows(self, request, pk=None):
        """
        Retrieves the first five rows of an ImportFile.
        """
        org_id = self.get_organization(request)
        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )
        if import_file.cached_second_to_fifth_row is None:
            return JsonResponse(
                {"status": "error", "message": "Internal problem occurred, import file first five rows not cached"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        """
        import_file.cached_second_to_fifth_row is a field that contains the first
        5 lines of data from the file, split on newlines, delimited by
        ROW_DELIMITER. This becomes an issue when fields have newlines in them,
        so the following is to handle newlines in the fields.
        In the case of only one data column there will be no ROW_DELIMITER.
        """
        header = import_file.cached_first_row.split(ROW_DELIMITER)
        data = import_file.cached_second_to_fifth_row
        return JsonResponse({"status": "success", "first_five_rows": convert_first_five_rows_to_list(header, data)})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "raw_columns": ["string"]})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def raw_column_names(self, request, pk=None):
        """
        Retrieves a list of all column names from an ImportFile.
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        return JsonResponse({"status": "success", "raw_columns": import_file.first_row_columns})

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request=AutoSchemaHelper.json_body({"inventory_type": (("all", "all"), ("properties", "properties"), ("taxlots", "taxlots"))}),
        responses={200: PROGRESS_DATA_SCHEMA},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"], url_path="mapping_results")
    def mapping_results(self, request, pk=None):
        """
        Starts a background task that collects the mapped Properties and/or Tax Lots (`inventory_type`, defaulting
        to "all") of an import file. When it completes, the results are available from
        `GET /api/v3/cache_entries/{unique_id}/`, using the `unique_id` of the returned progress data.
        """
        import_file_id = pk
        org_id = self.get_organization(request)
        inventory_type = request.data.get("inventory_type", "all")

        progress_data = ProgressData(func_name="mapping_results", unique_id=f"{org_id}{randint(10000, 99999)}")
        progress_key = progress_data.key
        args = {
            "import_file_id": import_file_id,
            "inventory_type": inventory_type,
            "org_id": org_id,
            "progress_key": progress_key,
        }

        mapping_results_task.s(args).apply_async()

        return progress_data.result()

    @staticmethod
    def _data_logger_is_accessible(request, org_id, data_logger_id):
        """Whether the data logger belongs to a property in the organization and the user's access level subtree"""
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        return DataLogger.objects.filter(
            pk=data_logger_id,
            property__organization_id=org_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).exists()

    @staticmethod
    def has_coparent(state_id, inventory_type):
        """
        Return the coparent of the current state id based on the inventory type. If fields
        are given (as a list), then it will only return the fields specified of the state model
        object as a dictionary.

        :param state_id: int, ID of PropertyState or TaxLotState
        :param inventory_type: string, either properties | taxlots
        :return: dict or state object, If fields is not None then will return state_object
        """
        state_model = PropertyState if inventory_type == "properties" else TaxLotState

        # TODO: convert coparent to instance method, not class method
        audit_entry, audit_count = state_model.coparent(state_id)

        if audit_count == 0:
            return False

        if audit_count > 1:
            return JsonResponse(
                {"status": "error", "message": "Internal problem occurred, more than one merge record found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return audit_entry[0]

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request=AutoSchemaHelper.json_body(
            {
                "remap": "boolean",
                "mark_as_done": "boolean",
            },
            description="- remap: delete previously mapped records first (default: false)\n"
            "- mark_as_done: mark the mapping as done when it completes (default: true)",
        ),
        responses={200: PROGRESS_DATA_SCHEMA},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def map(self, request, pk=None):
        """
        Starts a background task to convert imported raw data into
        PropertyState and TaxLotState, using user's column mappings.
        """

        body = request.data

        remap = body.get("remap", False)
        mark_as_done = body.get("mark_as_done", True)

        org_id = self.get_organization(request)
        import_file = ImportFile.objects.filter(pk=pk, import_record__super_organization_id=org_id)
        if not import_file.exists():
            return {"status": "error", "message": f"ImportFile {pk} does not exist"}

        return JsonResponse(map_data(pk, remap, mark_as_done))

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=None,
        responses={
            200: {
                "type": "object",
                "properties": {"progress_data": PROGRESS_DATA_SCHEMA, "sub_progress_data": PROGRESS_DATA_SCHEMA},
                "description": "If matching was already done, a single (warning) progress data object is returned instead",
            }
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def start_system_matching_and_geocoding(self, request, pk=None):
        """
        Starts a background task to attempt automatic matching between buildings
        in an ImportFile with other existing buildings within the same org.
        """
        org_id = self.get_organization(request)

        try:
            ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        return geocode_and_match_buildings_task(pk)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=None,
        responses={
            200: {
                "type": "object",
                "properties": {"progress_key": {"type": "string"}, "progress": PROGRESS_DATA_SCHEMA},
            }
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def start_data_quality_checks(self, request, pk=None):
        """
        Runs the data quality rules against an import file to get a preliminary
        assessment of issues before importing.
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        return_value = do_checks(org_id, None, None, None, import_file.pk)
        # step 5: create a new model instance
        return JsonResponse(
            {
                "progress_key": return_value["progress_key"],
                "progress": return_value,
            }
        )

    @extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()], request=None, responses={200: PROGRESS_DATA_SCHEMA})
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def validate_use_cases(self, request, pk=None):
        """
        Starts a background task to call BuildingSync's use case validation
        tool.
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        return task_validate_use_cases(import_file.pk)

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request=AutoSchemaHelper.json_body(
            {"cycle_id": "integer", "multiple_cycle_upload": "boolean"},
            required=["cycle_id"],
            description="- cycle_id: the cycle to save the data to\n"
            "- multiple_cycle_upload: assign each record to the cycle containing its year_ending, "
            "falling back to cycle_id (default: false)",
        ),
        responses={200: PROGRESS_DATA_SCHEMA},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def start_save_data(self, request, pk=None):
        """
        Starts a background task to import raw data from an ImportFile
        into PropertyState objects as extra_data. If the cycle_id is set to
        year_ending then the cycle ID will be set to the year_ending column for each
        record in the uploaded file. Note that the year_ending flag is not yet enabled.
        """
        body = request.data
        import_file_id = pk
        if not import_file_id:
            return JsonResponse({"status": "error", "message": "must pass file_id of file to save"}, status=status.HTTP_400_BAD_REQUEST)

        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=import_file_id, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        cycle_id = body.get("cycle_id")
        multiple_cycle_upload = body.get("multiple_cycle_upload", False)
        if not cycle_id:
            return JsonResponse(
                {"status": "error", "message": "must pass cycle_id of the cycle to save the data"}, status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # find the cycle
            cycle = Cycle.objects.filter(id=cycle_id, organization_id=org_id).first()
            if cycle:
                # assign the cycle id to the import file object
                import_file.cycle = cycle
                import_file.multiple_cycle_upload = multiple_cycle_upload
                import_file.save()
            else:
                return JsonResponse({"status": "error", "message": "cycle_id was invalid"}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(task_save_raw(import_file.id))

    @extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()], request=None, responses={200: STATUS_MESSAGE_SCHEMA})
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def mapping_done(self, request, pk=None):
        """
        Tell the backend that the mapping is complete.
        """
        import_file_id = pk
        if not import_file_id:
            return JsonResponse({"status": "error", "message": "must pass import_file_id"}, status=status.HTTP_400_BAD_REQUEST)

        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=import_file_id, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse({"status": "error", "message": "no import file with given id"}, status=status.HTTP_404_NOT_FOUND)

        import_file.mapping_done = True
        import_file.save()

        return JsonResponse({"status": "success", "message": ""})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "import_file_records": "integer",
                    "multiple_cycle_upload": "boolean",
                    "properties": MATCHING_RESULTS_COUNTS,
                    "tax_lots": MATCHING_RESULTS_COUNTS,
                }
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def matching_and_geocoding_results(self, request, pk=None):
        """
        Retrieves the number of matched and unmatched properties & tax lots for
        a given ImportFile record.  Specifically for new imports
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        # property views associated with this imported file (including merges)
        properties_new = []
        properties_matched = list(
            PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_MERGED,
            ).values_list("id", flat=True)
        )

        # Check audit log in case PropertyStates are listed as "new" but were merged into a different property
        properties = list(
            PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_NEW,
            )
        )

        for state in properties:
            audit_creation_id = (
                PropertyAuditLog.objects.only("id").exclude(import_filename=None).get(state_id=state.id, name="Import Creation")
            )
            if PropertyAuditLog.objects.exclude(record_type=AUDIT_USER_EDIT).filter(parent1_id=audit_creation_id).exists():
                properties_matched.append(state.id)
            else:
                properties_new.append(state.id)

        tax_lots_new = []
        tax_lots_matched = list(
            TaxLotState.objects.only("id")
            .filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_MERGED,
            )
            .values_list("id", flat=True)
        )

        # Check audit log in case TaxLotStates are listed as "new" but were merged into a different tax lot
        taxlots = list(
            TaxLotState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_NEW,
            )
        )

        for state in taxlots:
            audit_creation_id = (
                TaxLotAuditLog.objects.only("id").exclude(import_filename=None).get(state_id=state.id, name="Import Creation")
            )
            if TaxLotAuditLog.objects.exclude(record_type=AUDIT_USER_EDIT).filter(parent1_id=audit_creation_id).exists():
                tax_lots_matched.append(state.id)
            else:
                tax_lots_new.append(state.id)

        # Construct Geocode Results
        property_geocode_results = {
            "high_confidence": len(
                PropertyState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="High"
                )
            ),
            "low_confidence": len(
                PropertyState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="Low"
                )
            ),
            "census_geocoder": len(
                PropertyState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="Census"
                )
            ),
            "manual": len(
                PropertyState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence="Manually geocoded (N/A)"
                )
            ),
            "missing_address_components": len(
                PropertyState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence="Missing address components (N/A)"
                )
            ),
        }

        tax_lot_geocode_results = {
            "high_confidence": len(
                TaxLotState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="High"
                )
            ),
            "low_confidence": len(
                TaxLotState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="Low"
                )
            ),
            "census_geocoder": len(
                TaxLotState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence__startswith="Census"
                )
            ),
            "manual": len(
                TaxLotState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence="Manually geocoded (N/A)"
                )
            ),
            "missing_address_components": len(
                TaxLotState.objects.filter(
                    import_file__pk=import_file.pk, data_state=DATA_STATE_MATCHING, geocoding_confidence="Missing address components (N/A)"
                )
            ),
        }

        # merge in any of the matching results from the JSON field
        return {
            "status": "success",
            "import_file_records": import_file.matching_results_data.get("import_file_records", None),
            "multiple_cycle_upload": import_file.multiple_cycle_upload,
            "properties": {
                "initial_incoming": import_file.matching_results_data.get("property_initial_incoming", None),
                "duplicates_against_existing": import_file.matching_results_data.get("property_duplicates_against_existing", None),
                "duplicates_within_file": import_file.matching_results_data.get("property_duplicates_within_file", None),
                "duplicates_within_file_errors": import_file.matching_results_data.get("property_duplicates_within_file_errors", None),
                "merges_against_existing": import_file.matching_results_data.get("property_merges_against_existing", None),
                "merges_against_existing_errors": import_file.matching_results_data.get("property_merges_against_existing_errors", None),
                "merges_between_existing": import_file.matching_results_data.get("property_merges_between_existing", None),
                "merges_within_file": import_file.matching_results_data.get("property_merges_within_file", None),
                "merges_within_file_errors": import_file.matching_results_data.get("property_merges_within_file_errors", None),
                "new": import_file.matching_results_data.get("property_new", None),
                "new_errors": import_file.matching_results_data.get("property_new_errors", None),
                "geocoded_high_confidence": property_geocode_results.get("high_confidence"),
                "geocoded_low_confidence": property_geocode_results.get("low_confidence"),
                "geocoded_census_geocoder": property_geocode_results.get("census_geocoder"),
                "geocoded_manually": property_geocode_results.get("manual"),
                "geocode_not_possible": property_geocode_results.get("missing_address_components"),
            },
            "tax_lots": {
                "initial_incoming": import_file.matching_results_data.get("tax_lot_initial_incoming", None),
                "duplicates_against_existing": import_file.matching_results_data.get("tax_lot_duplicates_against_existing", None),
                "duplicates_within_file": import_file.matching_results_data.get("tax_lot_duplicates_within_file", None),
                "duplicates_within_file_errors": import_file.matching_results_data.get("tax_lot_duplicates_within_file_errors", None),
                "merges_against_existing": import_file.matching_results_data.get("tax_lot_merges_against_existing", None),
                "merges_against_existing_errors": import_file.matching_results_data.get("tax_lot_merges_against_existing_errors", None),
                "merges_between_existing": import_file.matching_results_data.get("tax_lot_merges_between_existing", None),
                "merges_within_file": import_file.matching_results_data.get("tax_lot_merges_within_file", None),
                "merges_within_file_errors": import_file.matching_results_data.get("tax_lot_merges_within_file_errors", None),
                "new": import_file.matching_results_data.get("tax_lot_new", None),
                "new_errors": import_file.matching_results_data.get("tax_lot_new_errors", None),
                "geocoded_high_confidence": tax_lot_geocode_results.get("high_confidence"),
                "geocoded_low_confidence": tax_lot_geocode_results.get("low_confidence"),
                "geocoded_census_geocoder": tax_lot_geocode_results.get("census_geocoder"),
                "geocoded_manually": tax_lot_geocode_results.get("manual"),
                "geocode_not_possible": tax_lot_geocode_results.get("missing_address_components"),
            },
        }

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "suggested_column_mappings": {
                        "type": "object",
                        "additionalProperties": {"type": "array", "items": {}, "minItems": 3, "maxItems": 3},
                        "description": "Raw column name to `[table_name, column_name, confidence]`",
                    },
                    "property_columns": {"type": "array", "items": {"type": "object"}, "description": "Mappable property columns"},
                    "taxlot_columns": {"type": "array", "items": {"type": "object"}, "description": "Mappable tax lot columns"},
                },
            }
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def mapping_suggestions(self, request, pk):
        """
        Returns suggested mappings from an uploaded file's headers to known
        data fields.
        """
        organization_id = self.get_organization(request)

        result = {"status": "success"}

        membership = OrganizationUser.objects.select_related("organization").get(organization_id=organization_id, user=request.user)
        organization = membership.organization

        # For now, each organization holds their own mappings. This is non-ideal, but it is the
        # way it is for now. In order to move to parent_org holding, then we need to be able to
        # dynamically match columns based on the names and not the db id (or support many-to-many).
        # parent_org = organization.get_parent()

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=organization.pk)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get a list of the database fields in a list, these are the db columns and the extra_data columns
        property_columns = Column.retrieve_mapping_columns(organization.pk, "property")
        taxlot_columns = Column.retrieve_mapping_columns(organization.pk, "taxlot")

        # If this is a portfolio manager file, then load in the PM mappings and if the column_mappings
        # are not in the original mappings, default to PM
        if import_file.from_portfolio_manager:
            pm_mappings = simple_mapper.get_pm_mapping(import_file.first_row_columns, resolve_duplicates=True)
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization_id),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                default_mappings=pm_mappings,
                thresh=80,
            )
        elif import_file.from_buildingsync:
            bsync_mappings = xml_mapper.build_column_mapping()
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization_id),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                default_mappings=bsync_mappings,
                thresh=80,
            )
        else:
            # All other input types
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization.pk),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                thresh=80,  # percentage match that we require. 80% is random value for now.
            )
            # replace None with empty string for column names and PropertyState for tables
            # TODO #239: Move this fix to build_column_mapping
            for m in suggested_mappings:
                table, destination_field, _confidence = suggested_mappings[m]
                if destination_field is None:
                    suggested_mappings[m][1] = ""

        # Fix the table name, eventually move this to the build_column_mapping
        for m in suggested_mappings:
            table, _destination_field, _confidence = suggested_mappings[m]
            # Do not return the created or updated fields... that is force them
            # to be in the property state. Not sure how this happens in this code though.
            if not table or table == "Property":
                suggested_mappings[m][0] = "PropertyState"
            elif table == "TaxLot":
                suggested_mappings[m][0] = "TaxLotState"

        result["suggested_column_mappings"] = suggested_mappings
        result["property_columns"] = property_columns
        result["taxlot_columns"] = taxlot_columns

        return JsonResponse(result)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={200: AutoSchemaHelper.schema_factory({"status": "string"})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    def destroy(self, request, pk):
        """
        Deletes an import file
        """
        organization_id = int(self.get_organization(request))
        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=organization_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        # check if the import record exists for the file and organization
        d = ImportRecord.objects.filter(super_organization_id=organization_id, pk=import_file.import_record.pk)

        if not d.exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "user does not have permission to delete file",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # This does not actually delete the object because it is a NonDeletableModel
        import_file.delete()
        return JsonResponse({"status": "success"})

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("view_id", required=False, description="ID of the property view to import to"),
            AutoSchemaHelper.query_integer_field("system_id", required=False, description="ID of the system to import to"),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"validated_type_units": VALIDATED_TYPE_UNITS, "proposed_imports": [METER_PROPOSED_IMPORT]}
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def greenbutton_meters_preview(self, request, pk):
        """
        Returns validated type units and proposed imports. Exactly one of `view_id` or `system_id` is required.
        """
        org_id = self.get_organization(request)
        view_id = request.query_params.get("view_id")
        system_id = request.query_params.get("system_id")
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        if view_id is not None and system_id is not None:
            return JsonResponse(
                {"status": "error", "message": "Must pass either view_id or system_id, not both"}, status=status.HTTP_400_BAD_REQUEST
            )
        elif view_id is not None:
            try:
                property_id = PropertyView.objects.get(
                    pk=view_id,
                    cycle__organization_id=org_id,
                    property__access_level_instance__lft__gte=access_level_instance.lft,
                    property__access_level_instance__rgt__lte=access_level_instance.rgt,
                ).property_id
            except PropertyView.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Could not find property with pk=" + str(view_id)}, status=status.HTTP_404_NOT_FOUND
                )
        elif system_id is not None:
            try:
                system_id = System.objects.get(
                    pk=system_id,
                    group__organization_id=org_id,
                    group__access_level_instance__lft__gte=access_level_instance.lft,
                    group__access_level_instance__rgt__lte=access_level_instance.rgt,
                ).id
            except System.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Could not find system with pk=" + str(system_id)}, status=status.HTTP_400_BAD_REQUEST
                )
            property_id = None
        else:
            return JsonResponse({"status": "error", "message": "Must pass view_id or system_id"}, status=status.HTTP_400_BAD_REQUEST)

        result = {}
        meters_parser = MetersParser.factory(
            import_file.local_file, org_id, source_type=Meter.GREENBUTTON, property_id=property_id, system_id=system_id
        )
        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports

        import_file.matching_results_data["property_id"] = property_id
        import_file.matching_results_data["system_id"] = system_id
        import_file.save()

        return result

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("view_id", required=True, description="ID of the property view to import to"),
            AutoSchemaHelper.query_integer_field("data_logger_id", required=False, description="ID of the data logger to import to"),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "proposed_imports": [
                        {
                            "column_name": "string",
                            "display_name": "string",
                            "type": "string",
                            "units": "string",
                            "location_description": "string",
                            "description": "string",
                        }
                    ]
                }
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
            has_hierarchy_access(param_property_view_id="view_id"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def sensors_preview(self, request, pk):
        """
        Returns the sensors that would be imported from a sensor metadata file
        """
        org_id = self.get_organization(request)
        view_id = request.query_params.get("view_id")
        data_logger_id = request.query_params.get("data_logger_id")

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            PropertyView.objects.get(pk=view_id, cycle__organization_id=org_id)
        except PropertyView.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find property with pk=" + str(view_id)}, status=status.HTTP_400_BAD_REQUEST
            )

        if data_logger_id is not None and not self._data_logger_is_accessible(request, org_id, data_logger_id):
            return JsonResponse(
                {"status": "error", "message": "Could not find data logger with pk=" + str(data_logger_id)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parser = reader.MCMParser(import_file.local_file)
        result = {"proposed_imports": list(parser.data)}

        import_file.matching_results_data["data_logger_id"] = data_logger_id
        import_file.save()

        return result

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("data_logger_id", required=False, description="ID of the data logger to import to"),
        ],
        responses={200: AutoSchemaHelper.schema_factory([{"column_name": "string", "exists": "boolean", "num_readings": "integer"}])},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def sensor_readings_preview(self, request, pk):
        """
        Returns, for each sensor column of a sensor readings file, whether the sensor exists and how many readings it has
        """
        org_id = self.get_organization(request)
        data_logger_id = request.query_params.get("data_logger_id")

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        if data_logger_id is not None and not self._data_logger_is_accessible(request, org_id, data_logger_id):
            return JsonResponse(
                {"status": "error", "message": "Could not find data logger with pk=" + str(data_logger_id)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sensor_readings_parser = SensorsReadingsParser.factory(import_file.local_file, org_id, data_logger_id=data_logger_id)
        except ValueError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        result = sensor_readings_parser.get_validation_report()

        import_file.matching_results_data["data_logger_id"] = data_logger_id
        import_file.save()

        return result

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "validated_type_units": VALIDATED_TYPE_UNITS,
                    "proposed_imports": [{**METER_PROPOSED_IMPORT, "pm_property_id": "string", "cycles": "string"}],
                    "unlinkable_pm_ids": [{"portfolio_manager_id": "string"}],
                }
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def pm_meters_preview(self, request, pk):
        """
        Returns validated type units, proposed imports and unlinkable PM ids
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
            meters_parser = MetersParser.factory(import_file.local_file, org_id, access_level_instance=import_file.access_level_instance)
            import_file.num_rows = len(meters_parser.proposed_imports)
            import_file.save()

        except ImportFile.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not find import file with pk=" + str(pk)}, status=status.HTTP_400_BAD_REQUEST
            )

        result = {}
        result["validated_type_units"] = meters_parser.validated_type_units()
        result["proposed_imports"] = meters_parser.proposed_imports
        result["unlinkable_pm_ids"] = meters_parser.unlinkable_pm_ids

        return result

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body({"meter_id": "integer"}, required=["meter_id"]),
        responses={200: STATUS_MESSAGE_SCHEMA},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def system_meter_upload(self, request, pk):
        """
        Imports the readings of a file (with "Start Date", "End Date", "Reading", and "Usage Units" columns) into a meter
        """
        org_id = self.get_organization(request)
        org = Organization.objects.get(pk=org_id)
        meter_id = request.data.get("meter_id")
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        meter = Meter.objects.filter(
            Q(
                property__organization_id=org_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )
            | Q(
                system__group__organization_id=org_id,
                system__group__access_level_instance__lft__gte=access_level_instance.lft,
                system__group__access_level_instance__rgt__lte=access_level_instance.rgt,
            ),
            pk=meter_id,
        ).first()
        if meter is None:
            return JsonResponse(
                {"status": "error", "message": f"Could not find meter with pk={meter_id}"}, status=status.HTTP_404_NOT_FOUND
            )

        import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        parser = reader.MCMParser(import_file.local_file)

        _kbtu_thermal_conversion_factors = kbtu_thermal_conversion_factors(org.get_thermal_conversion_assumption_display())
        _kgal_water_conversion_factors = kgal_water_conversion_factors(org.get_thermal_conversion_assumption_display())

        num_total_readings = 0
        num_readings_created = 0
        num_readings_updated = 0
        for raw_reading in parser.data:
            conversion_factor = get_conversion_factor(
                Meter.ENERGY_TYPE_BY_METER_TYPE[meter.type],
                raw_reading["Usage Units"],
                _kbtu_thermal_conversion_factors,
                _kgal_water_conversion_factors,
            )
            if conversion_factor is None:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"meter type {Meter.ENERGY_TYPE_BY_METER_TYPE[meter.type]} cannot be converted to {raw_reading['Usage Units']}.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # process dates
            the_tz = django_timezone.get_default_timezone()
            unaware_start = datetime.strptime(raw_reading["Start Date"], "%Y-%m-%d %H:%M:%S")
            unaware_end = datetime.strptime(raw_reading["End Date"], "%Y-%m-%d %H:%M:%S")
            start_time = localize_datetime_with_dst_fallbacks(unaware_start, the_tz)
            end_time = localize_datetime_with_dst_fallbacks(unaware_end, the_tz)

            # if a meter readings file is re-uploaded, it will UPDATE the values in defaults
            # rather than keeping the values and ignoring incoming new data
            # this code was really hard to get right due to the methods not respecting the
            # meter ID constraint and updating multiple records.

            # First, try to get the existing reading for this specific meter
            # also count how many readings were returned
            existing_readings = MeterReading.objects.filter(meter_id=meter.id, start_time=start_time, end_time=end_time)
            existing_reading = existing_readings.first() if existing_readings.count() > 0 else None

            if existing_reading:
                # Update using queryset.update() instead of instance.save()
                MeterReading.objects.filter(meter_id=meter.id, start_time=start_time, end_time=end_time).update(
                    reading=float(raw_reading["Reading"]) * conversion_factor,
                    conversion_factor=conversion_factor,
                    source_unit=raw_reading["Usage Units"],
                )
                created = False
            else:
                # Create new reading
                MeterReading.objects.create(
                    meter_id=meter.id,
                    start_time=start_time,
                    end_time=end_time,
                    reading=float(raw_reading["Reading"]) * conversion_factor,
                    conversion_factor=conversion_factor,
                    source_unit=raw_reading["Usage Units"],
                )
                created = True

            num_total_readings += 1
            if created:
                num_readings_created += 1
            else:
                num_readings_updated += 1

        return JsonResponse(
            {
                "status": "success",
                "message": f"{num_readings_created} new readings created and {num_readings_updated} updated from the {num_total_readings} readings found.",
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=None,
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "message": "string"},
                description='`status` is "warning" and `message` describes the problems when blank values were found',
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("can_modify_data"),
            has_hierarchy_access(import_file_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def verify_data_type_mapping(self, request, pk):
        """
        Verify that non-text columns don't contain null values, indicatative of data type mapping errors.
        """
        org_id = self.get_organization(request)

        try:
            import_file = ImportFile.objects.get(pk=pk, import_record__super_organization_id=org_id)
        except ImportFile.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_400_BAD_REQUEST)
        verify_data_types(org_id, import_file.id)
        import_file.refresh_from_db()

        warnings = import_file.mapping_error_messages
        response_status = "warning" if warnings else "success"
        return JsonResponse({"status": response_status, "message": warnings})


def get_conversion_factor(type_name, unit, _kbtu_thermal_conversion_factors, _kgal_water_conversion_factors):
    thermal_conversion_factor = _kbtu_thermal_conversion_factors.get(type_name, {}).get(unit, None)
    water_conversion_factor = _kgal_water_conversion_factors.get(type_name, {}).get(unit, None)

    return thermal_conversion_factor or water_conversion_factor
