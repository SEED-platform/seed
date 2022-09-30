# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import csv
import datetime
import logging
import os

import pint
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from past.builtins import basestring
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    parser_classes,
    permission_classes
)
from rest_framework.parsers import FormParser, MultiPartParser

from seed.data_importer.models import ROW_DELIMITER, ImportFile, ImportRecord
from seed.data_importer.tasks import do_checks
from seed.data_importer.tasks import \
    geocode_buildings_task as task_geocode_buildings
from seed.data_importer.tasks import \
    map_additional_models as task_map_additional_models
from seed.data_importer.tasks import map_data
from seed.data_importer.tasks import match_buildings as task_match_buildings
from seed.data_importer.tasks import save_raw_data as task_save_raw
from seed.data_importer.tasks import \
    validate_use_cases as task_validate_use_cases
from seed.decorators import ajax_request, ajax_request_class, get_prog_key
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.lib.xml_mapping import mapper as xml_mapper
from seed.models import (
    AUDIT_USER_EDIT,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    MERGE_STATE_UNKNOWN,
    PORTFOLIO_RAW,
    SEED_DATA_SOURCES,
    Column,
    Cycle,
    PropertyAuditLog,
    PropertyState,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    get_column_mapping,
    obj_to_dict
)
from seed.utils.api import api_endpoint, api_endpoint_class
from seed.utils.cache import get_cache
from seed.utils.geocode import MapQuestAPIKeyError

_log = logging.getLogger(__name__)


class LocalUploaderViewSet(viewsets.ViewSet):
    """
    Endpoint to upload data files to, if uploading to local file storage.
    Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

    Returns::

        {
            'success': True,
            'import_file_id': The ID of the newly-uploaded ImportFile
        }

    """

    @api_endpoint_class
    @ajax_request_class
    @parser_classes((MultiPartParser, FormParser,))
    def create(self, request):
        """
        Upload a new file to an import_record. This is a multipart/form upload.
        ---
        parameters:
            - name: import_record
              description: the ID of the ImportRecord to associate this file with.
              required: true
              paramType: body
            - name: source_type
              description: the type of file (e.g., 'Portfolio Raw' or 'Assessed Raw')
              required: false
              paramType: body
            - name: source_program_version
              description: the version of the file as related to the source_type
              required: false
              paramType: body
            - name: file or qqfile
              description: In-memory file object
              required: true
              paramType: Multipart
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        # Fineuploader requires the field to be qqfile it appears... so why not support both? ugh.
        if 'qqfile' in request.data:
            the_file = request.data['qqfile']
        else:
            the_file = request.data['file']
        filename = the_file.name
        path = os.path.join(settings.MEDIA_ROOT, "uploads", filename)

        # Get a unique filename using the get_available_name method in FileSystemStorage
        s = FileSystemStorage()
        path = s.get_available_name(path)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # save the file
        with open(path, 'wb+') as temp_file:
            for chunk in the_file.chunks():
                temp_file.write(chunk)

        import_record_pk = request.POST.get('import_record', request.GET.get('import_record'))
        try:
            record = ImportRecord.objects.get(pk=import_record_pk)
        except ImportRecord.DoesNotExist:
            # clean up the uploaded file
            os.unlink(path)
            return JsonResponse({
                'success': False,
                'message': "Import Record %s not found" % import_record_pk
            })

        source_type = request.POST.get('source_type', request.GET.get('source_type'))

        # Add Program & Version fields (empty string if not given)
        kw_fields = {field: request.POST.get(field, request.GET.get(field, ''))
                     for field in ['source_program', 'source_program_version']}

        f = ImportFile.objects.create(import_record=record,
                                      uploaded_filename=filename,
                                      file=path,
                                      source_type=source_type,
                                      **kw_fields)

        return JsonResponse({'success': True, "import_file_id": f.pk})

    @staticmethod
    def _get_pint_var_from_pm_value_object(pm_value):
        units = pint.UnitRegistry()
        if '@uom' in pm_value and '#text' in pm_value:
            # this is the correct expected path for unit-based attributes
            string_value = pm_value['#text']
            try:
                float_value = float(string_value)
            except ValueError:
                return {'success': False,
                        'message': 'Could not cast value to float: \"%s\"' % string_value}
            original_unit_string = pm_value['@uom']
            if original_unit_string == 'kBtu':
                pint_val = float_value * units.kBTU
            elif original_unit_string == 'kBtu/ft²':
                pint_val = float_value * units.kBTU / units.sq_ft
            elif original_unit_string == 'Metric Tons CO2e':
                pint_val = float_value * units.metric_ton
            elif original_unit_string == 'kgCO2e/ft²':
                pint_val = float_value * units.kilogram / units.sq_ft
            else:
                return {'success': False,
                        'message': 'Unsupported units string: \"%s\"' % original_unit_string}
            return {'success': True, 'pint_value': pint_val}

    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def create_from_pm_import(self, request):
        """
        Create an import_record from a PM import request.
        TODO: The properties key here is going to be an enormous amount of XML data at times, need to change this
        This allows the PM import workflow to be treated essentially the same as a standard file upload
        The process comprises the following steps:

        * Get a unique file name for this portfolio manager import
        *

        ---
        parameters:
            - name: import_record
              description: the ID of the ImportRecord to associate this file with.
              required: true
              paramType: body
            - name: properties
              description: In-memory list of properties from PM import
              required: true
              paramType: body
        """

        doing_pint = False

        if 'properties' not in request.data:
            return JsonResponse({
                'success': False,
                'message': "Must pass properties in the request body."
            }, status=status.HTTP_400_BAD_REQUEST)

        # base file name (will be appended with a random string to ensure uniqueness if multiple on the same day)
        today_date = datetime.datetime.today().strftime('%Y-%m-%d')
        file_name = "pm_import_%s.csv" % today_date

        # create a folder to keep pm_import files
        path = os.path.join(settings.MEDIA_ROOT, "uploads", "pm_imports", file_name)

        # Get a unique filename using the get_available_name method in FileSystemStorage
        s = FileSystemStorage()
        path = s.get_available_name(path)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # This list should cover the core keys coming from PM, ensuring that they map easily
        # We will also look for keys not in this list and just map them to themselves
        # pm_key_to_column_heading_map = {
        #     'address_1': 'Address',
        #     'city': 'City',
        #     'state_province': 'State',
        #     'postal_code': 'Zip',
        #     'county': 'County',
        #     'country': 'Country',
        #     'property_name': 'Property Name',
        #     'property_id': 'Property ID',
        #     'year_built': 'Year Built',
        # }
        # so now it looks like we *don't* need to override these, but instead we should leave all the headers as-is
        # I'm going to leave this in here for right now, but if it turns out that we don't need it after testing,
        # then I'll remove it entirely
        pm_key_to_column_heading_map = {}

        # We will also create a list of values that are used in PM export to indicate a value wasn't available
        # When we import them into SEED here we will be sure to not write those values
        pm_flagged_bad_string_values = [
            'Not Available',
            'Unable to Check (not enough data)',
            'No Current Year Ending Date',
        ]

        # We will make a pass through the first property to get the list of unexpected keys
        for pm_property in request.data['properties']:
            for pm_key_name, _ in pm_property.items():
                if pm_key_name not in pm_key_to_column_heading_map:
                    pm_key_to_column_heading_map[pm_key_name] = pm_key_name
            break

        # Create the header row of the csv file first
        rows = []
        header_row = []
        for _, csv_header in pm_key_to_column_heading_map.items():
            header_row.append(csv_header)
        rows.append(header_row)

        num_properties = len(request.data['properties'])
        property_num = 0
        last_time = datetime.datetime.now()

        _log.debug("About to try to import %s properties from ESPM" % num_properties)
        _log.debug("Starting at %s" % last_time)

        # Create a single row for each building
        for pm_property in request.data['properties']:

            # report some helpful info every 20 properties
            property_num += 1
            if property_num % 20 == 0:
                new_time = datetime.datetime.now()
                _log.debug("On property number %s; current time: %s" % (property_num, new_time))

            this_row = []

            # Loop through all known PM variables
            for pm_variable, _ in pm_key_to_column_heading_map.items():

                # Initialize this to False for each pm_variable we will search through
                added = False

                # Check if this PM export has this variable in it
                if pm_variable in pm_property:

                    # If so, create a convenience variable to store it
                    this_pm_variable = pm_property[pm_variable]

                    # Next we need to check type.  If it is a string, we will add it here to avoid parsing numerics
                    # However, we need to be sure to not add the flagged bad strings.
                    # However, a flagged value *could* be a value property name, and we would want to allow that
                    if isinstance(this_pm_variable, basestring):
                        if pm_variable == 'property_name':
                            this_row.append(this_pm_variable)
                            added = True
                        elif pm_variable == 'property_notes':
                            sanitized_string = this_pm_variable.replace('\n', ' ')
                            this_row.append(sanitized_string)
                            added = True
                        elif this_pm_variable not in pm_flagged_bad_string_values:
                            this_row.append(this_pm_variable)
                            added = True

                    # If it isn't a string, it should be a dictionary, storing numeric data and units, etc.
                    else:

                        # As long as it is a valid dictionary, try to get a meaningful value out of it
                        if this_pm_variable and '#text' in this_pm_variable and this_pm_variable['#text'] != 'Not Available':

                            # Coerce the value into a proper set of Pint units for us
                            if doing_pint:
                                new_var = LocalUploaderViewSet._get_pint_var_from_pm_value_object(this_pm_variable)
                                if new_var['success']:
                                    pint_value = new_var['pint_value']
                                    this_row.append(pint_value.magnitude)
                                    added = True
                                    # TODO: What to do with the pint_value.units here?
                            else:
                                this_row.append(float(this_pm_variable['#text']))
                                added = True

                # And finally, if we haven't set the added flag, give the csv column a blank value
                if not added:
                    this_row.append('')

            # Then add this property row of data
            rows.append(this_row)

        # Then write the actual data out as csv
        with open(path, 'w', encoding='utf-8') as csv_file:
            pm_csv_writer = csv.writer(csv_file)
            for row_num, row in enumerate(rows):
                pm_csv_writer.writerow(row)

        # Look up the import record (data set)
        import_record_pk = request.data['import_record_id']
        try:
            record = ImportRecord.objects.get(pk=import_record_pk)
        except ImportRecord.DoesNotExist:
            # clean up the uploaded file
            os.unlink(path)
            return JsonResponse({
                'success': False,
                'message': "Import Record %s not found" % import_record_pk
            })

        # Create a new import file object in the database
        f = ImportFile.objects.create(import_record=record,
                                      uploaded_filename=file_name,
                                      file=path,
                                      source_type=SEED_DATA_SOURCES[PORTFOLIO_RAW],
                                      **{'source_program': 'PortfolioManager',
                                         'source_program_version': '1.0'})

        # Return the newly created import file ID
        return JsonResponse({'success': True, 'import_file_id': f.pk})


@api_endpoint
@ajax_request
@login_required
@api_view(['GET'])
def get_upload_details(request):
    """
    Retrieves details about how to upload files to this instance.

    Returns::

        {
            'upload_path': The url to POST files to (see local_uploader)
        }

    """
    ret = {
        'upload_path': '/api/v3/upload/'
    }
    return JsonResponse(ret)


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
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            import_file:
                type: ImportFile structure
                description: full detail of import file
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
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
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            first_five_rows:
                type: array of strings
                description: list of strings for each of the first five rows for this import file
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
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
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            raw_columns:
                type: array of strings
                description: list of strings of the header row of the ImportFile
        parameter_strategy: replace
        parameters:
            - name: pk
              description: "Primary Key"
              required: true
              paramType: path
        """
        import_file = ImportFile.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'raw_columns': import_file.first_row_columns
        })

    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['POST'], url_path='filtered_mapping_results')
    def filtered_mapping_results(self, request, pk=None):
        """
        Retrieves a paginated list of Properties and Tax Lots for an import file after mapping.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import File ID (Primary key)
              type: integer
              required: true
              paramType: path
        response_serializer: MappingResultsResponseSerializer
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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def perform_mapping(self, request, pk=None):
        """
        Starts a background task to convert imported raw data into
        PropertyState and TaxLotState, using user's column mappings.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            progress_key:
                type: integer
                description: ID of background job, for retrieving job progress
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
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
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            progress_key:
                type: integer
                description: ID of background job, for retrieving job progress
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def start_data_quality_checks(self, request, pk=None):
        """
        Starts a background task to attempt automatic matching between buildings
        in an ImportFile with other existing buildings within the same org.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            progress_key:
                type: integer
                description: ID of background job, for retrieving job progress
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        return_value = do_checks(organization.id, None, None, pk)
        # step 5: create a new model instance
        return JsonResponse({
            'progress_key': return_value['progress_key'],
            'progress': return_value,
        })

    @api_endpoint_class
    @ajax_request_class
    @action(detail=True, methods=['GET'])
    def data_quality_progress(self, request, pk=None):
        """
        Return the progress of the data quality check.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            progress:
                type: integer
                description: status of background data quality task
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
        """

        import_file_id = pk
        prog_key = get_prog_key('get_progress', import_file_id)
        cache = get_cache(prog_key)
        return HttpResponse(cache['progress'])

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def validate_use_cases(self, request, pk=None):
        """
        Starts a background task to call BuildingSync's use case validation
        tool.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                required: false
                type: string
                description: error message, if any
            progress_key:
                type: integer
                description: ID of background job, for retrieving job progress
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
        """
        import_file_id = pk
        if not import_file_id:
            return JsonResponse({
                'status': 'error',
                'message': 'must include pk of import_file to validate'
            }, status=status.HTTP_400_BAD_REQUEST)

        return task_validate_use_cases(import_file_id)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def save_raw_data(self, request, pk=None):
        """
        Starts a background task to import raw data from an ImportFile
        into PropertyState objects as extra_data. If the cycle_id is set to
        year_ending then the cycle ID will be set to the year_ending column for each
        record in the uploaded file. Note that the year_ending flag is not yet enabled.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                required: false
                type: string
                description: error message, if any
            progress_key:
                type: integer
                description: ID of background job, for retrieving job progress
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
            - name: cycle_id
              description: The ID of the cycle or the string "year_ending"
              paramType: string
              required: true
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
    @action(detail=True, methods=['PUT'])
    def mapping_done(self, request, pk=None):
        """
        Tell the backend that the mapping is complete.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                required: false
                type: string
                description: error message, if any
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
        """
        import_file_id = pk
        if not import_file_id:
            return JsonResponse({
                'status': 'error',
                'message': 'must pass import_file_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        import_file = ImportFile.objects.get(pk=import_file_id)
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
    @action(detail=True, methods=['POST'])
    def save_column_mappings(self, request, pk=None):
        """
        Saves the mappings between the raw headers of an ImportFile and the
        destination fields in the `to_table_name` model which should be either
        PropertyState or TaxLotState

        Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

        Payload::

            {
                "import_file_id": ID of the ImportFile record,
                "mappings": [
                    {
                        'from_field': 'eui',  # raw field in import file
                        'from_units': 'kBtu/ft**2/year', # pint-parsable units, optional
                        'to_field': 'energy_use_intensity',
                        'to_field_display_name': 'Energy Use Intensity',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'gfa',
                        'from_units': 'ft**2', # pint-parsable units, optional
                        'to_field': 'gross_floor_area',
                        'to_field_display_name': 'Gross Floor Area',
                        'to_table_name': 'PropertyState',
                    }
                ]
            }

        Returns::

            {'status': 'success'}
        """
        body = request.data
        import_file = ImportFile.objects.get(pk=pk)
        organization = import_file.import_record.super_organization
        mappings = body.get('mappings', [])
        result = Column.create_mappings(mappings, organization, request.user, import_file.id)

        if result:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def matching_and_geocoding_results(self, request, pk=None):
        """
        Retrieves the number of matched and unmatched properties & tax lots for
        a given ImportFile record.  Specifically for new imports

        :GET: Expects import_file_id corresponding to the ImportFile in question.

        Returns::

            {
                'status': 'success',
                'properties': {
                    'matched': Number of PropertyStates that have been matched,
                    'unmatched': Number of PropertyStates that are unmatched new imports
                },
                'tax_lots': {
                    'matched': Number of TaxLotStates that have been matched,
                    'unmatched': Number of TaxLotStates that are unmatched new imports
                }
            }

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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @permission_classes((SEEDOrgPermissions,))
    @action(detail=True, methods=['GET'])
    def mapping_suggestions(self, request, pk):
        """
        Returns suggested mappings from an uploaded file's headers to known
        data fields.
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            suggested_column_mappings:
                required: true
                type: dictionary
                description: Dictionary where (key, value) = (the column header from the file,
                      array of tuples (destination column, score))
            building_columns:
                required: true
                type: array
                description: A list of all possible columns
            building_column_types:
                required: true
                type: array
                description: A list of column types corresponding to the building_columns array
        parameter_strategy: replace
        parameters:
            - name: pk
              description: import_file_id
              required: true
              paramType: path
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query

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

    @api_endpoint_class
    @ajax_request_class
    @permission_classes((SEEDOrgPermissions,))
    @has_perm_class('requires_member')
    def destroy(self, request, pk):
        """
        Returns suggested mappings from an uploaded file's headers to known
        data fields.
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
        parameter_strategy: replace
        parameters:
            - name: pk
              description: import_file_id
              required: true
              paramType: path
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query

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
