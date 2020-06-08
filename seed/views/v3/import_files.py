# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import (
    action,
    permission_classes,
)

from seed.data_importer.models import (
    ImportFile,
    ImportRecord
)
from seed.data_importer.models import ROW_DELIMITER
from seed.data_importer.tasks import do_checks
from seed.data_importer.tasks import (
    map_data,
    geocode_buildings_task as task_geocode_buildings,
    map_additional_models as task_map_additional_models,
    match_buildings as task_match_buildings,
    save_raw_data as task_save_raw,
)
from seed.decorators import ajax_request_class
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mcm import mapper
from seed.lib.xml_mapping import mapper as xml_mapper
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization,
)
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.models import (
    get_column_mapping,
)
from seed.models import (
    obj_to_dict,
    PropertyState,
    TaxLotState,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    MERGE_STATE_UNKNOWN,
    MERGE_STATE_NEW,
    MERGE_STATE_MERGED,
    Cycle,
    Column,
    PropertyAuditLog,
    TaxLotAuditLog,
    AUDIT_USER_EDIT,
    TaxLotProperty,
)
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.geocode import MapQuestAPIKeyError

_log = logging.getLogger(__name__)


class MappingResultsPropertySerializer(serializers.Serializer):
    pm_property_id = serializers.CharField(max_length=100)
    address_line_1 = serializers.CharField(max_length=100)
    property_name = serializers.CharField(max_length=100)


class MappingResultsTaxLotSerializer(serializers.Serializer):
    pm_property_id = serializers.CharField(max_length=100)
    address_line_1 = serializers.CharField(max_length=100)
    jurisdiction_tax_lot_id = serializers.CharField(max_length=100)


class MappingResultsResponseSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=100)
    properties = MappingResultsPropertySerializer(many=True)
    tax_lots = MappingResultsTaxLotSerializer(many=True)


def convert_first_five_rows_to_list(header, first_five_rows):
    """
    Return the first five rows. This is a complicated method because it handles converting the
    persisted format of the first five rows into a list of dictionaries. It handles some basic
    logic if there are crlf in the fields. Note that this method does not cover all the use cases
    and cannot due to the custom delimeter. See the tests in
    test_views.py:test_get_first_five_rows_newline_should_work to see the limitation

    :param header: list, ordered list of headers as strings
    :param first_five_rows: string, long string with |#*#| delimeter.
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
        rows = first_five_rows.splitlines()
    else:
        for idx, l in enumerate(split_cells):
            crlf_count = l.count('\n')

            if crlf_count == 0:
                row_data.append(l)
            elif crlf_count >= 1:
                # if add this element to row_data equals number_of_columns, then it is a new row
                if len(row_data) == number_of_columns - 1:
                    # check if this is the last columns, if so, then just store the value and move on
                    if idx == number_cells - 1:
                        row_data.append(l)
                        rows.append(row_data)
                        continue
                    else:
                        # split the cell_data. The last cell becomes the beginning of the new
                        # row, and the other cells stay joined with \n.
                        cell_data = l.splitlines()
                        row_data.append('\n'.join(cell_data[:crlf_count]))
                        rows.append(row_data)

                        # initialize the next row_data with the remainder
                        row_data = [cell_data[-1]]
                        continue
                else:
                    # this is not the end, so it must be a carriage return in the cell, just save data
                    row_data.append(l)

            if len(row_data) == number_of_columns:
                rows.append(row_data)

    return [dict(zip(header, row)) for row in rows]


class ImportFileViewSet(viewsets.ViewSet):
    raise_exception = True
    queryset = ImportFile.objects.all()

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Retrieves details about an ImportFile.
        """
        import_file_id = pk
        orgs = request.user.orgs.all()
        try:
            import_file = ImportFile.objects.get(
                pk=import_file_id
            )
            d = ImportRecord.objects.filter(
                super_organization__in=orgs, pk=import_file.import_record_id
            )
        except ObjectDoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not access an import file with this ID'
            }, status=status.HTTP_403_FORBIDDEN)
        # check if user has access to the import file
        if not d.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Could not locate import file with this ID',
                'import_file': {},
            }, status=status.HTTP_400_BAD_REQUEST)

        f = obj_to_dict(import_file)
        f['name'] = import_file.filename_only
        if not import_file.uploaded_filename:
            f['uploaded_filename'] = import_file.filename
        f['dataset'] = obj_to_dict(import_file.import_record)

        return JsonResponse({
            'status': 'success',
            'import_file': f,
        })

    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def first_five_rows(self, request, pk=None):
        """
        Retrieves the first five rows of an ImportFile.
        """
        import_file = ImportFile.objects.get(pk=pk)
        if import_file is None:
            return JsonResponse(
                {'status': 'error', 'message': 'Could not find import file with pk=' + str(
                    pk)}, status=status.HTTP_400_BAD_REQUEST)
        if import_file.cached_second_to_fifth_row is None:
            return JsonResponse({'status': 'error',
                                 'message': 'Internal problem occurred, import file first five rows not cached'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        '''
        import_file.cached_second_to_fifth_row is a field that contains the first
        5 lines of data from the file, split on newlines, delimited by
        ROW_DELIMITER. This becomes an issue when fields have newlines in them,
        so the following is to handle newlines in the fields.
        In the case of only one data column there will be no ROW_DELIMITER.
        '''
        header = import_file.cached_first_row.split(ROW_DELIMITER)
        data = import_file.cached_second_to_fifth_row
        return JsonResponse({
            'status': 'success',
            'first_five_rows': convert_first_five_rows_to_list(header, data)
        })

    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def raw_column_names(self, request, pk=None):
        """
        Retrieves a list of all column names from an ImportFile.
        """
        import_file = ImportFile.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'raw_columns': import_file.first_row_columns
        })

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.org_id_field(),
        ],
        responses={
            200: MappingResultsResponseSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['POST'], url_path='filtered_mapping_results')
    def filtered_mapping_results(self, request, pk=None):
        """
        Retrieves a paginated list of Properties and Tax Lots for an import file after mapping.
        """
        import_file_id = pk
        org_id = request.query_params.get('organization_id', False)

        # get the field names that were in the mapping
        import_file = ImportFile.objects.get(id=import_file_id)

        # List of the only fields to show
        field_names = import_file.get_cached_mapped_columns

        # set of fields
        fields = {
            'PropertyState': ['id', 'extra_data', 'lot_number'],
            'TaxLotState': ['id', 'extra_data']
        }
        columns_from_db = Column.retrieve_all(org_id)
        property_column_name_mapping = {}
        taxlot_column_name_mapping = {}
        for field_name in field_names:
            # find the field from the columns in the database
            for column in columns_from_db:
                if column['table_name'] == 'PropertyState' and \
                        field_name[0] == 'PropertyState' and \
                        field_name[1] == column['column_name']:
                    property_column_name_mapping[column['column_name']] = column['name']
                    if not column['is_extra_data']:
                        fields['PropertyState'].append(field_name[1])  # save to the raw db fields
                    continue
                elif column['table_name'] == 'TaxLotState' and \
                        field_name[0] == 'TaxLotState' and \
                        field_name[1] == column['column_name']:
                    taxlot_column_name_mapping[column['column_name']] = column['name']
                    if not column['is_extra_data']:
                        fields['TaxLotState'].append(field_name[1])  # save to the raw db fields
                    continue

        inventory_type = request.data.get('inventory_type', 'all')

        result = {
            'status': 'success'
        }

        if inventory_type == 'properties' or inventory_type == 'all':
            properties = PropertyState.objects.filter(
                import_file_id=import_file_id,
                data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
                merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
            ).only(*fields['PropertyState']).order_by('id')

            property_results = []
            for prop in properties:
                prop_dict = TaxLotProperty.model_to_dict_with_mapping(
                    prop,
                    property_column_name_mapping,
                    fields=fields['PropertyState'],
                    exclude=['extra_data']
                )

                prop_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        prop.extra_data,
                        property_column_name_mapping,
                        fields=prop.extra_data.keys(),
                    ).items()
                )
                property_results.append(prop_dict)

            result['properties'] = property_results

        if inventory_type == 'taxlots' or inventory_type == 'all':
            tax_lots = TaxLotState.objects.filter(
                import_file_id=import_file_id,
                data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
                merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
            ).only(*fields['TaxLotState']).order_by('id')

            tax_lot_results = []
            for tax_lot in tax_lots:
                tax_lot_dict = TaxLotProperty.model_to_dict_with_mapping(
                    tax_lot,
                    taxlot_column_name_mapping,
                    fields=fields['TaxLotState'],
                    exclude=['extra_data']
                )
                tax_lot_dict.update(
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        tax_lot.extra_data,
                        taxlot_column_name_mapping,
                        fields=tax_lot.extra_data.keys(),
                    ).items()
                )
                tax_lot_results.append(tax_lot_dict)

            result['tax_lots'] = tax_lot_results

        return result

    @staticmethod
    def has_coparent(state_id, inventory_type, fields=None):
        """
        Return the coparent of the current state id based on the inventory type. If fields
        are given (as a list), then it will only return the fields specified of the state model
        object as a dictionary.

        :param state_id: int, ID of PropertyState or TaxLotState
        :param inventory_type: string, either properties | taxlots
        :param fields: list, either None or list of fields to return
        :return: dict or state object, If fields is not None then will return state_object
        """
        state_model = PropertyState if inventory_type == 'properties' else TaxLotState

        # TODO: convert coparent to instance method, not class method
        audit_entry, audit_count = state_model.coparent(state_id)

        if audit_count == 0:
            return False

        if audit_count > 1:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Internal problem occurred, more than one merge record found'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return audit_entry[0]

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory({
            'remap': 'boolean',
            'mark_as_done': 'boolean',
        })
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def map(self, request, pk=None):
        """
        Starts a background task to convert imported raw data into
        PropertyState and TaxLotState, using user's column mappings.
        """

        body = request.data

        remap = body.get('remap', False)
        mark_as_done = body.get('mark_as_done', True)
        if not ImportFile.objects.filter(pk=pk).exists():
            return {
                'status': 'error',
                'message': 'ImportFile {} does not exist'.format(pk)
            }

        # return remap_data(import_file_id)
        return JsonResponse(map_data(pk, remap, mark_as_done))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def start_system_matching_and_geocoding(self, request, pk=None):
        """
        Starts a background task to attempt automatic matching between buildings
        in an ImportFile with other existing buildings within the same org.
        """
        try:
            task_geocode_buildings(pk)
        except MapQuestAPIKeyError:
            result = JsonResponse({
                'status': 'error',
                'message': 'MapQuest API key may be invalid or at its limit.'
            }, status=status.HTTP_403_FORBIDDEN)
            return result

        try:
            import_file = ImportFile.objects.get(pk=pk)
        except ImportFile.DoesNotExist:
            return {
                'status': 'error',
                'message': 'ImportFile {} does not exist'.format(pk)
            }

        # if the file is BuildingSync, don't do the merging, but instead finish
        # creating it's associated models (scenarios, meters, etc)
        if import_file.from_buildingsync:
            return task_map_additional_models(pk)

        return task_match_buildings(pk)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.org_id_field()])
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def start_data_quality_checks(self, request, pk=None):
        """
        Starts a background task to attempt automatic matching between buildings
        in an ImportFile with other existing buildings within the same org.
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        return_value = do_checks(organization.id, None, None, pk)
        # step 5: create a new model instance
        return JsonResponse({
            'progress_key': return_value['progress_key'],
            'progress': return_value,
        })

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory({'cycle_id': 'string'})
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
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
            return JsonResponse({
                'status': 'error',
                'message': 'must pass file_id of file to save'
            }, status=status.HTTP_400_BAD_REQUEST)

        cycle_id = body.get('cycle_id')
        if not cycle_id:
            return JsonResponse({
                'status': 'error',
                'message': 'must pass cycle_id of the cycle to save the data'
            }, status=status.HTTP_400_BAD_REQUEST)
        elif cycle_id == 'year_ending':
            _log.error("NOT CONFIGURED FOR YEAR ENDING OPTION AT THE MOMENT")
            return JsonResponse({
                'status': 'error',
                'message': 'SEED is unable to parse year_ending at the moment'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # find the cycle
            cycle = Cycle.objects.get(id=cycle_id)
            if cycle:
                # assign the cycle id to the import file object
                import_file = ImportFile.objects.get(id=import_file_id)
                import_file.cycle = cycle
                import_file.save()
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'cycle_id was invalid'
                }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(task_save_raw(import_file_id))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def mapping_done(self, request, pk=None):
        """
        Tell the backend that the mapping is complete.
        """
        import_file_id = pk
        if not import_file_id:
            return JsonResponse({
                'status': 'error',
                'message': 'must pass import_file_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            import_file = ImportFile.objects.get(pk=import_file_id)
        except ImportFile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'no import file with given id'
            }, status=status.HTTP_404_NOT_FOUND)

        import_file.mapping_done = True
        import_file.save()

        return JsonResponse(
            {
                'status': 'success',
                'message': ''
            }
        )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def matching_and_geocoding_results(self, request, pk=None):
        """
        Retrieves the number of matched and unmatched properties & tax lots for
        a given ImportFile record.  Specifically for new imports
        """
        import_file = ImportFile.objects.get(pk=pk)

        # property views associated with this imported file (including merges)
        properties_new = []
        properties_matched = list(PropertyState.objects.filter(
            import_file__pk=import_file.pk,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_MERGED,
        ).values_list('id', flat=True))

        # Check audit log in case PropertyStates are listed as "new" but were merged into a different property
        properties = list(PropertyState.objects.filter(
            import_file__pk=import_file.pk,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_NEW,
        ))

        for state in properties:
            audit_creation_id = PropertyAuditLog.objects.only('id').exclude(
                import_filename=None).get(
                state_id=state.id,
                name='Import Creation'
            )
            if PropertyAuditLog.objects.exclude(record_type=AUDIT_USER_EDIT).filter(
                parent1_id=audit_creation_id
            ).exists():
                properties_matched.append(state.id)
            else:
                properties_new.append(state.id)

        tax_lots_new = []
        tax_lots_matched = list(TaxLotState.objects.only('id').filter(
            import_file__pk=import_file.pk,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_MERGED,
        ).values_list('id', flat=True))

        # Check audit log in case TaxLotStates are listed as "new" but were merged into a different tax lot
        taxlots = list(TaxLotState.objects.filter(
            import_file__pk=import_file.pk,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_NEW,
        ))

        for state in taxlots:
            audit_creation_id = TaxLotAuditLog.objects.only('id').exclude(import_filename=None).get(
                state_id=state.id,
                name='Import Creation'
            )
            if TaxLotAuditLog.objects.exclude(record_type=AUDIT_USER_EDIT).filter(
                parent1_id=audit_creation_id
            ).exists():
                tax_lots_matched.append(state.id)
            else:
                tax_lots_new.append(state.id)

        # Construct Geocode Results
        property_geocode_results = {
            'high_confidence': len(PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence__startswith='High'
            )),
            'low_confidence': len(PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence__startswith='Low'
            )),
            'manual': len(PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence='Manually geocoded (N/A)'
            )),
            'missing_address_components': len(PropertyState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence='Missing address components (N/A)'
            )),
        }

        tax_lot_geocode_results = {
            'high_confidence': len(TaxLotState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence__startswith='High'
            )),
            'low_confidence': len(TaxLotState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence__startswith='Low'
            )),
            'manual': len(TaxLotState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence='Manually geocoded (N/A)'
            )),
            'missing_address_components': len(TaxLotState.objects.filter(
                import_file__pk=import_file.pk,
                data_state=DATA_STATE_MATCHING,
                geocoding_confidence='Missing address components (N/A)'
            )),
        }

        # merge in any of the matching results from the JSON field
        return {
            'status': 'success',
            'import_file_records': import_file.matching_results_data.get('import_file_records', None),
            'properties': {
                'initial_incoming': import_file.matching_results_data.get('property_initial_incoming', None),
                'duplicates_against_existing': import_file.matching_results_data.get('property_duplicates_against_existing', None),
                'duplicates_within_file': import_file.matching_results_data.get('property_duplicates_within_file', None),
                'merges_against_existing': import_file.matching_results_data.get('property_merges_against_existing', None),
                'merges_between_existing': import_file.matching_results_data.get('property_merges_between_existing', None),
                'merges_within_file': import_file.matching_results_data.get('property_merges_within_file', None),
                'new': import_file.matching_results_data.get('property_new', None),
                'geocoded_high_confidence': property_geocode_results.get('high_confidence'),
                'geocoded_low_confidence': property_geocode_results.get('low_confidence'),
                'geocoded_manually': property_geocode_results.get('manual'),
                'geocode_not_possible': property_geocode_results.get('missing_address_components'),
            },
            'tax_lots': {
                'initial_incoming': import_file.matching_results_data.get('tax_lot_initial_incoming', None),
                'duplicates_against_existing': import_file.matching_results_data.get('tax_lot_duplicates_against_existing', None),
                'duplicates_within_file': import_file.matching_results_data.get('tax_lot_duplicates_within_file', None),
                'merges_against_existing': import_file.matching_results_data.get('tax_lot_merges_against_existing', None),
                'merges_between_existing': import_file.matching_results_data.get('tax_lot_merges_between_existing', None),
                'merges_within_file': import_file.matching_results_data.get('tax_lot_merges_within_file', None),
                'new': import_file.matching_results_data.get('tax_lot_new', None),
                'geocoded_high_confidence': tax_lot_geocode_results.get('high_confidence'),
                'geocoded_low_confidence': tax_lot_geocode_results.get('low_confidence'),
                'geocoded_manually': tax_lot_geocode_results.get('manual'),
                'geocode_not_possible': tax_lot_geocode_results.get('missing_address_components'),
            }
        }

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.org_id_field()])
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @permission_classes((SEEDOrgPermissions,))
    @action(detail=True, methods=['GET'])
    def mapping_suggestions(self, request, pk):
        """
        Returns suggested mappings from an uploaded file's headers to known
        data fields.
        """
        organization_id = request.query_params.get('organization_id', None)

        result = {'status': 'success'}

        membership = OrganizationUser.objects.select_related('organization') \
            .get(organization_id=organization_id, user=request.user)
        organization = membership.organization

        # For now, each organization holds their own mappings. This is non-ideal, but it is the
        # way it is for now. In order to move to parent_org holding, then we need to be able to
        # dynamically match columns based on the names and not the db id (or support many-to-many).
        # parent_org = organization.get_parent()

        import_file = ImportFile.objects.get(
            pk=pk,
            import_record__super_organization_id=organization.pk
        )

        # Get a list of the database fields in a list, these are the db columns and the extra_data columns
        property_columns = Column.retrieve_mapping_columns(organization.pk, 'property')
        taxlot_columns = Column.retrieve_mapping_columns(organization.pk, 'taxlot')

        # If this is a portfolio manager file, then load in the PM mappings and if the column_mappings
        # are not in the original mappings, default to PM
        if import_file.from_portfolio_manager:
            pm_mappings = simple_mapper.get_pm_mapping(import_file.first_row_columns,
                                                       resolve_duplicates=True)
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization_id),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                default_mappings=pm_mappings,
                thresh=80
            )
        elif import_file.from_buildingsync:
            bsync_mappings = xml_mapper.build_column_mapping()
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization_id),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                default_mappings=bsync_mappings,
                thresh=80
            )
        else:
            # All other input types
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization.pk),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                thresh=80  # percentage match that we require. 80% is random value for now.
            )
            # replace None with empty string for column names and PropertyState for tables
            # TODO #239: Move this fix to build_column_mapping
            for m in suggested_mappings:
                table, destination_field, _confidence = suggested_mappings[m]
                if destination_field is None:
                    suggested_mappings[m][1] = ''

        # Fix the table name, eventually move this to the build_column_mapping
        for m in suggested_mappings:
            table, _destination_field, _confidence = suggested_mappings[m]
            # Do not return the campus, created, updated fields... that is force them to be in the property state
            if not table or table == 'Property':
                suggested_mappings[m][0] = 'PropertyState'
            elif table == 'TaxLot':
                suggested_mappings[m][0] = 'TaxLotState'

        result['suggested_column_mappings'] = suggested_mappings
        result['property_columns'] = property_columns
        result['taxlot_columns'] = taxlot_columns

        return JsonResponse(result)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.org_id_field()])
    @api_endpoint_class
    @ajax_request_class
    @permission_classes((SEEDOrgPermissions,))
    @has_perm_class('requires_member')
    def destroy(self, request, pk):
        """
        Deletes an import file
        """
        organization_id = int(request.query_params.get('organization_id', None))
        import_file = ImportFile.objects.get(pk=pk)

        # check if the import record exists for the file and organization
        d = ImportRecord.objects.filter(
            super_organization_id=organization_id,
            pk=import_file.import_record.pk
        )

        if not d.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'user does not have permission to delete file',
            }, status=status.HTTP_403_FORBIDDEN)

        # This does not actually delete the object because it is a NonDeletableModel
        import_file.delete()
        return JsonResponse({'status': 'success'})
