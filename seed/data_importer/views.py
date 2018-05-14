# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import base64
import csv
import hashlib
import hmac
import json
import logging
import os

import pint
from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view, detail_route, list_route, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser

from seed.data_importer.models import (
    ImportFile,
    ImportRecord
)
from seed.data_importer.models import ROW_DELIMITER
from seed.data_importer.tasks import (
    map_data,
    match_buildings,
    save_raw_data as task_save_raw
)
from seed.decorators import ajax_request, ajax_request_class
from seed.decorators import get_prog_key
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mcm import mapper
from seed.lib.merging import merging
from seed.lib.superperms.orgs.decorators import has_perm_class
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
    MERGE_STATE_DELETE,
    Cycle,
    Column,
    PropertyAuditLog,
    TaxLotAuditLog,
    PropertyView,
    TaxLotView,
    AUDIT_IMPORT,
    AUDIT_USER_EDIT,
    Property,
    TaxLot,
    TaxLotProperty,
    SEED_DATA_SOURCES,
    PORTFOLIO_RAW)
from seed.models.data_quality import DataQualityCheck
from seed.utils.api import api_endpoint, api_endpoint_class
from seed.utils.cache import get_cache_raw, get_cache

_log = logging.getLogger(__name__)


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def handle_s3_upload_complete(request):
    """
    Notify the system that an upload to S3 has been completed. This is
    a necessary step after uploading to S3 or the SEED instance will not
    be aware the file exists.

    Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

    :GET: Expects the following in the query string:

        key: The full path to the file, within the S3 bucket.
            E.g. data_importer/buildings.csv

        source_type: The source of the file.
            E.g. 'Assessed Raw' or 'Portfolio Raw'

        source_program: Optional value from common.mapper.Programs
        source_version: e.g. "4.1"

        import_record: The ID of the ImportRecord this file belongs to.

    Returns::

        {
            'success': True,
            'import_file_id': The ID of the newly-created ImportFile object.
        }
    """
    if 'S3' not in settings.DEFAULT_FILE_STORAGE:
        return {
            'success': False,
            'message': "Direct-to-S3 uploads not enabled"
        }

    import_record_pk = request.POST['import_record']
    try:
        record = ImportRecord.objects.get(pk=import_record_pk)
    except ImportRecord.DoesNotExist:
        # TODO: Remove the file from S3?
        return {
            'success': False,
            'message': "Import Record %s not found" % import_record_pk
        }

    filename = request.POST['key']
    source_type = request.POST['source_type']
    # Add Program & Version fields (empty string if not given)
    kw_fields = {
        f: request.POST.get(f, '') for f in ['source_program', 'source_program_version']
    }

    f = ImportFile.objects.create(import_record=record,
                                  file=filename,
                                  source_type=source_type,
                                  **kw_fields)
    return JsonResponse({'success': True, "import_file_id": f.pk})


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
              description: the type of file (e.g. 'Portfolio Raw' or 'Assessed Raw')
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

        # The s3 stuff needs to be redone someday... delete?
        if 'S3' in settings.DEFAULT_FILE_STORAGE:
            os.unlink(path)
            raise ImproperlyConfigured("Local upload not supported")  # TODO: Is this wording correct?

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
                return {'success': False, 'message': 'Could not cast value to float: \"%s\"' % string_value}
            original_unit_string = pm_value['@uom']
            if original_unit_string == u'kBtu':
                new_val = float_value * 1000  # convert to btu manually
                pint_val = new_val * units.BTU
            elif original_unit_string == u'kBtu/ft²':
                new_val = float_value * 1000  # convert to btu manually
                pint_val = new_val * units.BTU / units.sq_ft
            elif original_unit_string == u'Metric Tons CO2e':
                pint_val = float_value * units.metric_ton
            elif original_unit_string == u'kgCO2e/ft²':
                pint_val = float_value * units.kilogram / units.sq_ft
            else:
                return {'success': False, 'message': 'Unsupported units string: \"%s\"' % original_unit_string}
            return {'success': True, 'pint_value': pint_val}

    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['POST'])
    def create_from_pm_import(self, request):
        """
        Create an import_record from a PM import request.
        This allows the PM import workflow to be treated essentially the same as a standard file upload
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
        if 'properties' not in request.data:
            return JsonResponse({
                'success': False,
                'message': "Must pass pm_data in the request body."
            }, status=status.HTTP_400_BAD_REQUEST)

        # create a folder to keep pm_import files
        path = os.path.join(settings.MEDIA_ROOT, "uploads", "pm_imports", "pm_import.csv")

        # Get a unique filename using the get_available_name method in FileSystemStorage
        s = FileSystemStorage()
        path = s.get_available_name(path)

        # verify the directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # This list should cover the core keys coming from PM, ensuring that they map easily
        # We will also look for keys not in this list and just map them to themselves
        pm_key_to_column_heading_map = {
            u'address_1': u'Address',
            u'city': u'City',
            u'state_province': u'State',
            u'postal_code': u'Zip',
            u'county': u'County',
            u'country': u'Country',
            u'property_name': u'Property Name',
            u'property_id': u'Property ID',
            u'year_built': u'Year Built',
        }

        # We will also create a list of values that are used in PM export to indicate a value wasn't available
        # When we import them into SEED here we will be sure to not write those values
        pm_flagged_bad_string_values = [
            u'Not Available',
            u'Unable to Check (not enough data)',
            u'No Current Year Ending Date',
        ]

        # We will make a pass through the first property to get the list of unexpected keys
        for pm_property in request.data['properties']:
            for pm_key_name, _ in pm_property.iteritems():
                if pm_key_name not in pm_key_to_column_heading_map:
                    pm_key_to_column_heading_map[pm_key_name] = pm_key_name
            break

        # Create the header row of the csv file first
        rows = []
        this_row = []
        for _, csv_header in pm_key_to_column_heading_map.iteritems():
            this_row.append(csv_header)
        rows.append(this_row)

        # Create a single row for each building
        for pm_property in request.data['properties']:
            this_row = []

            # Loop through all known PM variables
            for pm_variable, _ in pm_key_to_column_heading_map.iteritems():

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
                        if pm_variable == u'property_name':
                            this_row.append(this_pm_variable)
                            added = True
                        elif this_pm_variable not in pm_flagged_bad_string_values:
                            this_row.append(this_pm_variable)
                            added = True

                    # If it isn't a string, it should be a dictionary, storing numeric data and units, etc.
                    else:

                        # As long as it is a valid dictionary, try to get a meaningful value out of it
                        if '#text' in this_pm_variable and this_pm_variable['#text'] != 'Not Available':

                            # Coerce the value into a proper set of Pint units for us
                            new_var = LocalUploaderViewSet._get_pint_var_from_pm_value_object(this_pm_variable)
                            if new_var['success']:
                                pint_value = new_var['pint_value']
                                this_row.append(pint_value.magnitude)
                                added = True
                                # TODO: What to do with the pint_value.units here?

                # And finally, if we haven't set the added flag, give the csv column a blank value
                if not added:
                    this_row.append(u'')

            # Then add this property row of data
            rows.append(this_row)

        # Then write the actual data out as csv
        with open(path, 'wb') as csv_file:
            pm_csv_writer = csv.writer(csv_file)
            for row in rows:
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
                                      uploaded_filename='PortfolioManagerImport',
                                      file=path,
                                      source_type=SEED_DATA_SOURCES[PORTFOLIO_RAW],
                                      **{'source_program': 'PortfolioManager', 'source_program_version': '1.0'})

        # Return the newly created import file ID
        return JsonResponse({'success': True, "import_file_id": f.pk})


@api_endpoint
@ajax_request
@login_required
@api_view(['GET'])
def get_upload_details(request):
    """
    Retrieves details about how to upload files to this instance.

    Returns::

        If S3 mode:

        {
            'upload_mode': 'S3',
            'upload_complete': A url to notify that upload is complete,
            'signature': The url to post file details to for auth to upload to S3.
        }

        If local file system mode:

        {
            'upload_mode': 'filesystem',
            'upload_path': The url to POST files to (see local_uploader)
        }

    """
    ret = {}
    if 'S3' in settings.DEFAULT_FILE_STORAGE:
        # S3 mode
        ret['upload_mode'] = 'S3'
        ret['upload_complete'] = reverse('api:v2:s3_upload_complete')
        ret['signature'] = reverse('api:v2:sign_policy_document')
        ret['aws_bucket_name'] = settings.AWS_BUCKET_NAME
        ret['aws_client_key'] = settings.AWS_UPLOAD_CLIENT_KEY
    else:
        ret['upload_mode'] = 'filesystem'
        ret['upload_path'] = '/api/v2/upload/'
    return JsonResponse(ret)


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def sign_policy_document(request):
    """
    Sign and return the policy document for a simple upload.
    http://aws.amazon.com/articles/1434/#signyours3postform

    Payload::

        {
         "expiration": ISO-encoded timestamp for when signature should expire,
                       e.g. "2014-07-16T00:20:56.277Z",
         "conditions":
             [
                 {"acl":"private"},
                 {"bucket": The name of the bucket from get_upload_details},
                 {"Content-Type":"text/csv"},
                 {"success_action_status":"200"},
                 {"key": filename of upload, prefixed with 'data_imports/',
                         suffixed with a unique timestamp.
                         e.g. 'data_imports/my_buildings.csv.1405469756'},
                 {"x-amz-meta-category":"data_imports"},
                 {"x-amz-meta-qqfilename": original filename}
             ]
        }

    Returns::

        {
            "policy": A hash of the policy document. Using during upload to S3.
            "signature": A signature of the policy document.  Also used during upload to S3.
        }
    """
    policy_document = request.data
    policy = base64.b64encode(json.dumps(policy_document))
    signature = base64.b64encode(
        hmac.new(
            settings.AWS_UPLOAD_CLIENT_SECRET_KEY, policy, hashlib.sha1
        ).digest()
    )
    return JsonResponse({
        'policy': policy,
        'signature': signature
    })


class MappingResultsPayloadSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=100)
    order_by = serializers.CharField(max_length=100)
    filter_params = JSONField()
    page = serializers.IntegerField()
    number_per_page = serializers.IntegerField()


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
        # add the importfiles for the matching select
        f['dataset']['importfiles'] = []
        files = f['dataset']['importfiles']
        for i in import_file.import_record.files:
            tmp_uploaded_filename = i.filename_only
            if i.uploaded_filename:
                tmp_uploaded_filename = i.uploaded_filename

            files.append({
                'name': i.filename_only,
                'uploaded_filename': tmp_uploaded_filename,
                'mapping_done': i.mapping_done,
                'cycle': i.cycle.id,
                'id': i.pk
            })

        # make the first element in the list the current import file
        i = next(index for (index, d) in enumerate(files) if d["id"] == import_file.pk)
        files[0], files[i] = files[i], files[0]

        return JsonResponse({
            'status': 'success',
            'import_file': f,
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
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
        lines = []
        number_of_columns = len(import_file.cached_first_row.split(ROW_DELIMITER))
        for l in import_file.cached_second_to_fifth_row.splitlines():
            if ROW_DELIMITER in l or number_of_columns == 1:
                lines.append(l)
            else:
                # Line caused by newline in data, concat it to previous line.
                index = len(lines) - 1
                lines[index] = lines[index] + '\n' + l

        rows = [r.split(ROW_DELIMITER) for r in lines]

        return JsonResponse({
            'status': 'success',
            'first_five_rows': [
                dict(
                    zip(import_file.first_row_columns, row)
                ) for row in rows
            ]
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
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
    @detail_route(methods=['POST'], url_path='filtered_mapping_results')
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

                prop_dict = dict(
                    prop_dict.items() +
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        prop.extra_data,
                        property_column_name_mapping
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
                tax_lot_dict = dict(
                    tax_lot_dict.items() +
                    TaxLotProperty.extra_data_to_dict_with_mapping(
                        tax_lot.extra_data,
                        taxlot_column_name_mapping
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
    @detail_route(methods=['POST'])
    def unmatch(self, request, pk=None):
        body = request.data

        # import_file_id = int(pk)
        inventory_type = body.get('inventory_type', 'properties')
        source_state_id = int(body.get('state_id', None))
        coparent_id = int(body.get('coparent_id', None))

        # Make sure the state isn't already unmatched
        coparent = self.has_coparent(source_state_id, inventory_type, ['id'])
        if not coparent:
            return JsonResponse({
                'status': 'error',
                'message': 'Source state is already unmatched'
            }, status=status.HTTP_400_BAD_REQUEST)

        if coparent['id'] != coparent_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Coparent ID in audit history doesn\'t match coparent_id parameter',
                'found': coparent.id,
                'passed_in': coparent_id
            }, status=status.HTTP_400_BAD_REQUEST)

        if inventory_type == 'properties':
            audit_log = PropertyAuditLog
            label = apps.get_model('seed', 'Property_labels')
            state = PropertyState
            view = PropertyView
        else:
            audit_log = TaxLotAuditLog
            label = apps.get_model('seed', 'TaxLot_labels')
            state = TaxLotState
            view = TaxLotView

        state1 = state.objects.get(id=coparent['id'])
        state2 = state.objects.get(id=source_state_id)

        merged_record = audit_log.objects.select_related('state', 'parent1', 'parent2').get(
            parent_state1__in=[state1, state2],
            parent_state2__in=[state1, state2]
        )

        # Ensure that state numbers line up with parent numbers
        if merged_record.parent_state1_id != state1.id:
            state1_copy = state1
            state1 = state2
            state2 = state1_copy

        merged_state = merged_record.state

        # Check if we are at the end of a merge tree
        if view.objects.filter(state=merged_state).exists():
            old_view = view.objects.get(state=merged_state)
            cycle_id = old_view.cycle_id

            # Clone the property/taxlot record, then the labels
            if inventory_type == 'properties':
                old_inventory = old_view.property
                label_ids = list(old_inventory.labels.all().values_list('id', flat=True))
                new_inventory = old_inventory
                new_inventory.id = None
                new_inventory.save()

                for label_id in label_ids:
                    label(property_id=new_inventory.id, statuslabel_id=label_id).save()
            else:
                old_inventory = old_view.taxlot
                label_ids = list(old_inventory.labels.all().values_list('id', flat=True))
                new_inventory = old_inventory
                new_inventory.id = None
                new_inventory.save()

                for label_id in label_ids:
                    label(taxlot_id=new_inventory.id, tatuslabel_id=label_id).save()

            # Create the views
            if inventory_type == 'properties':
                new_view1 = view(
                    cycle_id=cycle_id,
                    property_id=new_inventory.id,
                    state=state1
                )
                new_view2 = view(
                    cycle_id=cycle_id,
                    property_id=old_view.property_id,
                    state=state2
                )
            else:
                new_view1 = view(
                    cycle_id=cycle_id,
                    taxlot_id=new_inventory.id,
                    state=state1
                )
                new_view2 = view(
                    cycle_id=cycle_id,
                    taxlot_id=old_view.taxlot_id,
                    state=state2
                )

            # Mark the merged state as deleted
            merged_state.merge_state = MERGE_STATE_DELETE
            merged_state.save()

            # Change the merge_state of the individual states
            if merged_record.parent1.name in ['Import Creation',
                                              'Manual Edit'] and merged_record.parent1.import_filename is not None:
                # State belongs to a new record
                state1.merge_state = MERGE_STATE_NEW
            else:
                state1.merge_state = MERGE_STATE_MERGED
            if merged_record.parent2.name in ['Import Creation',
                                              'Manual Edit'] and merged_record.parent2.import_filename is not None:
                # State belongs to a new record
                state2.merge_state = MERGE_STATE_NEW
            else:
                state2.merge_state = MERGE_STATE_MERGED
            state1.save()
            state2.save()

            # Delete the audit log entry for the merge
            merged_record.delete()

            # Duplicate pairing
            if inventory_type == 'properties':
                paired_view_ids = list(TaxLotProperty.objects.filter(property_view_id=old_view.id)
                                       .order_by('taxlot_view_id').values_list('taxlot_view_id',
                                                                               flat=True))
            else:
                paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id=old_view.id)
                                       .order_by('property_view_id').values_list('property_view_id',
                                                                                 flat=True))

            old_view.delete()
            new_view1.save()
            new_view2.save()

            if inventory_type == 'properties':
                for paired_view_id in paired_view_ids:
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   property_view_id=new_view1.id,
                                   taxlot_view_id=paired_view_id).save()
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   property_view_id=new_view2.id,
                                   taxlot_view_id=paired_view_id).save()
            else:
                for paired_view_id in paired_view_ids:
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   taxlot_view_id=new_view1.id,
                                   property_view_id=paired_view_id).save()
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   taxlot_view_id=new_view2.id,
                                   property_view_id=paired_view_id).save()

        else:
            # We are somewhere in the middle of a merge tree
            # Climb the tree and find the final merge state
            done_searching = False
            current_merged_record = merged_record
            while not done_searching:
                # current_merged_record = audit_log.objects.select_related('state', 'parent1', 'parent2').filter(
                #     parent1__in=[state1, state2],
                #     parent_state2__in=[state1, state2]
                # )
                record = audit_log.objects.only('parent1_id', 'parent2_id') \
                    .filter(
                    Q(parent1_id=current_merged_record.id) | Q(parent2_id=current_merged_record.id))
                if record.exists():
                    current_merged_record = record.first()
                else:
                    final_merged_state = current_merged_record.state
                    done_searching = True

            old_view = view.objects.get(state=final_merged_state)
            cycle_id = old_view.cycle_id

            # Clone the property/taxlot record, then the labels
            if inventory_type == 'properties':
                old_inventory = old_view.property
                label_ids = list(old_inventory.labels.all().values_list('id', flat=True))
                new_inventory = old_inventory
                new_inventory.id = None
                new_inventory.save()

                for label_id in label_ids:
                    label(property_id=new_inventory.id, statuslabel_id=label_id).save()
            else:
                old_inventory = old_view.taxlot
                label_ids = list(old_inventory.labels.all().values_list('id', flat=True))
                new_inventory = old_inventory
                new_inventory.id = None
                new_inventory.save()

                for label_id in label_ids:
                    label(taxlot_id=new_inventory.id, statuslabel_id=label_id).save()

            # Create the view
            if inventory_type == 'properties':
                new_view = view(
                    cycle_id=cycle_id,
                    property_id=new_inventory.id,
                    state=state.objects.get(id=source_state_id)
                )
            else:
                new_view = view(
                    cycle_id=cycle_id,
                    taxlot_id=new_inventory.id,
                    state=state.objects.get(id=source_state_id)
                )

            # Change the merge_state of the individual states
            if merged_record.parent1.name in ['Import Creation',
                                              'Manual Edit'] and merged_record.parent1.import_filename is not None:
                # State belongs to a new record
                state1.merge_state = MERGE_STATE_NEW
            else:
                state1.merge_state = MERGE_STATE_MERGED
            if merged_record.parent2.name in ['Import Creation',
                                              'Manual Edit'] and merged_record.parent2.import_filename is not None:
                # State belongs to a new record
                state2.merge_state = MERGE_STATE_NEW
            else:
                state2.merge_state = MERGE_STATE_MERGED
            state1.save()
            state2.save()

            # Remove the parent from the original merge state record and make sure only parent1 is populated
            if merged_record.parent_state1_id == source_state_id:
                merged_record.parent_state1_id = merged_record.parent_state2_id
                merged_record.parent1_id = merged_record.parent2_id
            merged_record.parent_state2_id = None
            merged_record.parent2_id = None
            merged_record.save()

            # Duplicate pairing
            if inventory_type == 'properties':
                paired_view_ids = list(TaxLotProperty.objects.filter(property_view_id=old_view.id)
                                       .order_by('taxlot_view_id').values_list('taxlot_view_id',
                                                                               flat=True))
            else:
                paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id=old_view.id)
                                       .order_by('property_view_id').values_list('property_view_id',
                                                                                 flat=True))

            new_view.save()

            if inventory_type == 'properties':
                for paired_view_id in paired_view_ids:
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   property_view_id=new_view.id,
                                   taxlot_view_id=paired_view_id).save()
            else:
                for paired_view_id in paired_view_ids:
                    TaxLotProperty(primary=True,
                                   cycle_id=cycle_id,
                                   taxlot_view_id=new_view.id,
                                   property_view_id=paired_view_id).save()

        return {
            'status': 'success'
        }

    @api_endpoint_class
    @ajax_request_class
    @permission_classes((SEEDOrgPermissions,))
    @detail_route(methods=['POST'])
    def match(self, request, pk=None):
        body = request.data

        # import_file_id = pk
        inventory_type = body.get('inventory_type', 'properties')
        source_state_id = int(body.get('state_id', None))
        matching_state_id = int(body.get('matching_state_id', None))
        organization_id = int(request.query_params.get('organization_id', None))

        # Make sure the state isn't already matched
        if self.has_coparent(source_state_id, inventory_type):
            return JsonResponse({
                'status': 'error',
                'message': 'Source state is already matched'
            }, status=status.HTTP_400_BAD_REQUEST)

        if inventory_type == 'properties':
            audit_log = PropertyAuditLog
            inventory = Property
            label = apps.get_model('seed', 'Property_labels')
            state = PropertyState
            view = PropertyView
        else:
            audit_log = TaxLotAuditLog
            inventory = TaxLot
            label = apps.get_model('seed', 'TaxLot_labels')
            state = TaxLotState
            view = TaxLotView

        state1 = state.objects.get(id=matching_state_id)
        state2 = state.objects.get(id=source_state_id)

        merged_state = state.objects.create(organization_id=organization_id)
        merged_state, changes = merging.merge_state(merged_state,
                                                    state1,
                                                    state2,
                                                    merging.get_state_attrs([state1, state2]),
                                                    default=state2)

        state_1_audit_log = audit_log.objects.filter(state=state1).first()
        state_2_audit_log = audit_log.objects.filter(state=state2).first()

        audit_log.objects.create(organization=state1.organization,
                                 parent1=state_1_audit_log,
                                 parent2=state_2_audit_log,
                                 parent_state1=state1,
                                 parent_state2=state2,
                                 state=merged_state,
                                 name='Manual Match',
                                 description='Automatic Merge',
                                 import_filename=None,
                                 record_type=AUDIT_IMPORT)

        # Set the merged_state to merged
        merged_state.data_state = DATA_STATE_MATCHING
        merged_state.merge_state = MERGE_STATE_MERGED
        merged_state.save()
        state2.merge_state = MERGE_STATE_UNKNOWN
        state2.save()

        # Delete existing views and inventory records
        views = view.objects.filter(state_id__in=[source_state_id, matching_state_id])
        view_ids = list(views.values_list('id', flat=True))
        cycle_id = views.first().cycle_id
        label_ids = []
        # Get paired view ids
        if inventory_type == 'properties':
            paired_view_ids = list(TaxLotProperty.objects.filter(property_view_id__in=view_ids)
                                   .order_by('taxlot_view_id').distinct('taxlot_view_id')
                                   .values_list('taxlot_view_id', flat=True))
        else:
            paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id__in=view_ids)
                                   .order_by('property_view_id').distinct('property_view_id')
                                   .values_list('property_view_id', flat=True))
        for v in views:
            if inventory_type == 'properties':
                label_ids.extend(list(v.property.labels.all().values_list('id', flat=True)))
                v.property.delete()
            else:
                label_ids.extend(list(v.taxlot.labels.all().values_list('id', flat=True)))
                v.taxlot.delete()
        label_ids = list(set(label_ids))

        # Create new inventory record
        inventory_record = inventory(organization_id=organization_id)
        inventory_record.save()

        # Create new labels and view
        if inventory_type == 'properties':
            for label_id in label_ids:
                label(property_id=inventory_record.id, statuslabel_id=label_id).save()
            new_view = view(cycle_id=cycle_id, state_id=merged_state.id,
                            property_id=inventory_record.id)
        else:
            for label_id in label_ids:
                label(taxlot_id=inventory_record.id, statuslabel_id=label_id).save()
            new_view = view(cycle_id=cycle_id, state_id=merged_state.id,
                            taxlot_id=inventory_record.id)
        new_view.save()

        # Delete existing pairs and re-pair all to new view
        if inventory_type == 'properties':
            # Probably already deleted by cascade
            TaxLotProperty.objects.filter(property_view_id__in=view_ids).delete()
            for paired_view_id in paired_view_ids:
                TaxLotProperty(primary=True,
                               cycle_id=cycle_id,
                               property_view_id=new_view.id,
                               taxlot_view_id=paired_view_id).save()
        else:
            # Probably already deleted by cascade
            TaxLotProperty.objects.filter(taxlot_view_id__in=view_ids).delete()
            for paired_view_id in paired_view_ids:
                TaxLotProperty(primary=True,
                               cycle_id=cycle_id,
                               property_view_id=paired_view_id,
                               taxlot_view_id=new_view.id).save()

        return {
            'status': 'success'
        }

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['POST'])
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
    @detail_route(methods=['POST'])
    def start_system_matching(self, request, pk=None):
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
        return match_buildings(pk)

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'], url_path='data_quality_results')
    def get_data_quality_results(self, request, pk=None):
        """
        Retrieve the details of the data quality check.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                type: string
                description: additional information, if any
            progress:
                type: integer
                description: integer percent of completion
            data:
                type: JSON
                description: object describing the results of the data quality check
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID
              required: true
              paramType: path
        """
        import_file_id = pk
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(import_file_id))
        return JsonResponse({
            'status': 'success',
            'message': 'data quality check complete',
            'progress': 100,
            'data': data_quality_results
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
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
    @detail_route(methods=['POST'])
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
    @detail_route(methods=['PUT'])
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
    @detail_route(methods=['POST'])
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
                        'from_units': 'kBtu/ft**2/year', # pint-parseable units, optional
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'gfa',
                        'from_units': 'ft**2', # pint-parseable units, optional
                        'to_field': 'gross_floor_area',
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
        status = Column.create_mappings(mappings, organization, request.user, import_file.id)

        if status:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @detail_route(methods=['GET'])
    def matching_results(self, request, pk=None):
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
        import_file_id = pk

        # property views associated with this imported file (including merges)
        properties_new = []
        properties_matched = list(PropertyState.objects.filter(
            import_file__pk=import_file_id,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_MERGED,
        ).values_list('id', flat=True))

        # Check audit log in case PropertyStates are listed as "new" but were merged into a different property
        properties = list(PropertyState.objects.filter(
            import_file__pk=import_file_id,
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
            import_file__pk=import_file_id,
            data_state=DATA_STATE_MATCHING,
            merge_state=MERGE_STATE_MERGED,
        ).values_list('id', flat=True))

        # Check audit log in case TaxLotStates are listed as "new" but were merged into a different tax lot
        taxlots = list(TaxLotState.objects.filter(
            import_file__pk=import_file_id,
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

        return {
            'status': 'success',
            'properties': {
                'matched': len(properties_matched),
                'unmatched': len(properties_new)
            },
            'tax_lots': {
                'matched': len(tax_lots_matched),
                'unmatched': len(tax_lots_new)
            }
        }

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @detail_route(methods=['GET'])
    def matching_status(self, request, pk=None):
        """
        Retrieves the number and ids of matched and unmatched properties & tax lots for
        a given ImportFile record.  Specifically for hand-matching

        :GET: Expects import_file_id corresponding to the ImportFile in question.

        Returns::

            {
                'status': 'success',
                'properties': {
                    'matched': Number of PropertyStates that have been matched,
                    'matched_ids': Array of matched PropertyState ids,
                    'unmatched': Number of PropertyStates that are unmatched records,
                    'unmatched_ids': Array of unmatched PropertyState ids
                },
                'tax_lots': {
                    'matched': Number of TaxLotStates that have been matched,
                    'matched_ids': Array of matched TaxLotState ids,
                    'unmatched': Number of TaxLotStates that are unmatched records,
                    'unmatched_ids': Array of unmatched TaxLotState ids
                }
            }

        """
        import_file_id = pk

        inventory_type = request.query_params.get('inventory_type', 'all')

        result = {
            'status': 'success',
        }

        if inventory_type == 'properties' or inventory_type == 'all':
            # property views associated with this imported file (including merges)
            properties_new = []
            properties_matched = list(PropertyState.objects.filter(
                import_file__pk=import_file_id,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_MERGED,
            ).values_list('id', flat=True))

            # Check audit log in case PropertyStates are listed as "new" but were merged into a different property
            properties = list(PropertyState.objects.filter(
                import_file__pk=import_file_id,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_NEW,
            ))
            # If a record was manually edited then remove the edited version
            properties_to_remove = list(PropertyAuditLog.objects.filter(
                state__in=properties,
                name='Manual Edit'
            ).values_list('state_id', flat=True))
            properties = [p for p in properties if p.id not in properties_to_remove]

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

            result['properties'] = {
                'matched': len(properties_matched),
                'matched_ids': properties_matched,
                'unmatched': len(properties_new),
                'unmatched_ids': properties_new
            }

        if inventory_type == 'taxlots' or inventory_type == 'all':
            tax_lots_new = []
            tax_lots_matched = list(TaxLotState.objects.only('id').filter(
                import_file__pk=import_file_id,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_MERGED,
            ).values_list('id', flat=True))

            # Check audit log in case TaxLotStates are listed as "new" but were merged into a different tax lot
            taxlots = list(TaxLotState.objects.filter(
                import_file__pk=import_file_id,
                data_state=DATA_STATE_MATCHING,
                merge_state=MERGE_STATE_NEW,
            ))
            # If a record was manually edited then remove the edited version
            taxlots_to_remove = list(TaxLotAuditLog.objects.filter(
                state__in=taxlots,
                name='Manual Edit'
            ).values_list('state_id', flat=True))
            taxlots = [t for t in taxlots if t.id not in taxlots_to_remove]

            for state in taxlots:
                audit_creation_id = TaxLotAuditLog.objects.only('id').exclude(
                    import_filename=None).get(
                    state_id=state.id,
                    name='Import Creation'
                )
                if TaxLotAuditLog.objects.exclude(record_type=AUDIT_USER_EDIT).filter(
                    parent1_id=audit_creation_id
                ).exists():
                    tax_lots_matched.append(state.id)
                else:
                    tax_lots_new.append(state.id)

            result['tax_lots'] = {
                'matched': len(tax_lots_matched),
                'matched_ids': tax_lots_matched,
                'unmatched': len(tax_lots_new),
                'unmatched_ids': tax_lots_new
            }

        return result

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @permission_classes((SEEDOrgPermissions,))
    @detail_route(methods=['GET'])
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

        import_file = ImportFile.objects.get(
            pk=pk,
            import_record__super_organization_id=organization.pk
        )

        # Get a list of the database fields in a list, these are the db columns and the extra_data columns
        mapping_data = Column.retrieve_mapping_columns(organization_id)

        # I think we want column_name to be display_name, but need to change front end.
        column_names = [c['column_name'] for c in mapping_data]

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
                thresh=80
            )
        else:
            # All other input types
            suggested_mappings = mapper.build_column_mapping(
                import_file.first_row_columns,
                Column.retrieve_all_by_tuple(organization_id),
                previous_mapping=get_column_mapping,
                map_args=[organization],
                thresh=80  # percentage match that we require. 80% is random value for now.
            )
            # replace None with empty string for column names and PropertyState for tables
            for m in suggested_mappings:
                table, destination_field, _confidence = suggested_mappings[m]
                if destination_field is None:
                    suggested_mappings[m][1] = u''

        # Fix the table name, eventually move this to the build_column_mapping and build_pm_mapping
        for m in suggested_mappings:
            table, _destination_field, _confidence = suggested_mappings[m]
            if not table:
                suggested_mappings[m][0] = 'PropertyState'

        result['suggested_column_mappings'] = suggested_mappings
        result['column_names'] = column_names
        result['columns'] = mapping_data

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
