# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import base64
import csv
import hashlib
import hmac
import json
import logging
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view
from rest_framework.decorators import detail_route
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

from seed.authentication import SEEDAuthentication
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
from seed.lib.mappings.mapping_data import MappingData
from seed.lib.merging import merging
from seed.lib.superperms.orgs.decorators import has_perm_class
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
    TaxLotProperty)
from seed.models.data_quality import DataQualityCheck
from seed.utils.api import api_endpoint, api_endpoint_class
from seed.utils.cache import get_cache_raw, get_cache
from seed.views.main import _mapping_suggestions

_log = logging.getLogger(__name__)


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])  # NL -- this is a POST because, well, no idea. Can we just remove S3, plz?
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


class LocalUploaderViewSet(viewsets.GenericViewSet):
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
        if 'qqfile' in request.data.keys():
            the_file = request.data['qqfile']
        else:
            the_file = request.data['file']
        filename = the_file.name
        path = settings.MEDIA_ROOT + "/uploads/" + filename

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
            raise ImproperlyConfigured("Local upload not supported")

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
        ret['upload_complete'] = reverse('apiv2:s3_upload_complete')
        ret['signature'] = reverse('apiv2:sign_policy_document')
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
    number_properties_matching_search = serializers.IntegerField()
    number_properties_returned = serializers.IntegerField()
    number_tax_lots_matching_search = serializers.IntegerField()
    number_tax_lots_returned = serializers.IntegerField()


class ImportFileViewSet(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

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
    @detail_route(methods=['POST'])
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

        get_coparents = request.data.get('get_coparents', False)
        get_state_id = request.data.get('state_id', False)

        # get the field names that were in the mapping
        import_file = ImportFile.objects.get(id=import_file_id)
        field_names = import_file.get_cached_mapped_columns

        # get the columns in the db...
        md = MappingData()
        _log.debug('md.keys_with_table_names are: {}'.format(md.keys_with_table_names))

        raw_db_fields = []
        for db_field in md.keys_with_table_names:
            if db_field in field_names:
                raw_db_fields.append(db_field)

        # go through the list and find the ones that are properties
        fields = {
            'PropertyState': ['id', 'extra_data', 'lot_number'],
            'TaxLotState': ['id', 'extra_data']
        }
        for f in raw_db_fields:
            fields[f[0]].append(f[1])

        _log.debug('Field names that will be returned are: {}'.format(fields))

        if get_state_id:
            state_id = int(get_state_id)
            inventory_type = request.data.get('inventory_type', 'properties')
            result = {}
            if inventory_type == 'properties':
                state = PropertyState.objects.get(id=state_id)
                for k in fields['PropertyState']:
                    result[k] = getattr(state, k)
            else:
                state = TaxLotState.objects.get(id=state_id)
                for k in fields['TaxLotState']:
                    result[k] = getattr(state, k)

            if get_coparents:
                result['matched'] = False
                coparent = None
                if inventory_type == 'properties':
                    coparent = self.has_coparent(state.id, inventory_type, fields['PropertyState'])
                else:
                    coparent = self.has_coparent(state.id, inventory_type, fields['TaxLotState'])

                if coparent:
                    result['matched'] = True
                    result['coparent'] = coparent

            return {
                'status': 'success',
                'state': result
            }
        else:
            properties = list(PropertyState.objects.filter(
                import_file_id=import_file_id,
                data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
                merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
            ).order_by('id').values(*fields['PropertyState']))
            tax_lots = list(TaxLotState.objects.filter(
                import_file_id=import_file_id,
                data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
                merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
            ).order_by('id').values(*fields['TaxLotState']))

            # If a record was manually edited then remove the edited version
            properties_to_remove = list()
            taxlots_to_remove = list()

            for p in properties:
                if PropertyAuditLog.objects.filter(state_id=p['id'], name='Manual Edit').exists():
                    properties_to_remove.append(p['id'])
            for t in tax_lots:
                if TaxLotAuditLog.objects.filter(state_id=t['id'], name='Manual Edit').exists():
                    taxlots_to_remove.append(t['id'])

            properties = [p for p in properties if p['id'] not in properties_to_remove]
            tax_lots = [t for t in tax_lots if t['id'] not in taxlots_to_remove]

            if get_coparents:
                for state in properties:
                    state['matched'] = False
                    coparent = self.has_coparent(state['id'], 'properties', fields['PropertyState'])
                    if coparent:
                        state['matched'] = True
                        state['coparent'] = coparent

                for state in tax_lots:
                    state['matched'] = False
                    coparent = self.has_coparent(state['id'], 'taxlots', fields['TaxLotState'])
                    if coparent:
                        state['matched'] = True
                        state['coparent'] = coparent

            _log.debug('Found {} properties'.format(len(properties)))
            _log.debug('Found {} tax lots'.format(len(tax_lots)))

            return {
                'status': 'success',
                'properties': properties,
                'tax_lots': tax_lots,
                'number_properties_returned': len(properties),
                'number_properties_matching_search': len(properties),
                'number_tax_lots_returned': len(tax_lots),
                'number_tax_lots_matching_search': len(tax_lots),
            }

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['POST'])
    def available_matches(self, request, pk=None):
        body = request.data

        import_file_id = int(pk)
        inventory_type = body.get('inventory_type', 'properties')
        source_state_id = int(body.get('state_id', None))

        import_file = ImportFile.objects.get(id=import_file_id)
        field_names = import_file.get_cached_mapped_columns

        # get the columns in the db...
        md = MappingData()
        _log.debug('md.keys_with_table_names are: {}'.format(md.keys_with_table_names))

        raw_db_fields = []
        for db_field in md.keys_with_table_names:
            if db_field in field_names:
                raw_db_fields.append(db_field)

        # go through the list and find the ones that are properties
        fields = {
            'PropertyState': ['id', 'extra_data', 'lot_number'],
            'TaxLotState': ['id', 'extra_data']
        }
        for f in raw_db_fields:
            fields[f[0]].append(f[1])

        def state_to_dict(state):
            result = {}
            if inventory_type == 'properties':
                for k in fields['PropertyState']:
                    result[k] = getattr(state, k)
            else:
                for k in fields['TaxLotState']:
                    result[k] = getattr(state, k)
            return result

        if inventory_type == 'properties':
            views = PropertyView.objects.filter(cycle_id=import_file.cycle_id).select_related(
                'state')
        else:
            views = TaxLotView.objects.filter(cycle_id=import_file.cycle_id).select_related('state')

        source_state = {'found': False}
        states = []
        for v in views:
            if v.state_id == source_state_id:
                source_state['found'] = True
            else:
                states.append(v.state)

        results = []
        if inventory_type == 'properties':
            audit_log = PropertyAuditLog
        else:
            audit_log = TaxLotAuditLog

        # return true if initial state was inherited, or if the record was inherited from the same import file
        def check_audit_merge_history(audit_entry):
            if source_state['found']:
                return True

            if audit_entry.parent1_id:
                if audit_entry.parent_state1_id == source_state_id:
                    source_state['found'] = True
                    return True
                else:
                    result = check_audit_merge_history(audit_entry.parent1)
                    if result:
                        return True

            if audit_entry.parent2_id:
                if audit_entry.parent_state2_id == source_state_id:
                    source_state['found'] = True
                    return True
                else:
                    result = check_audit_merge_history(audit_entry.parent2)
                    if result:
                        return True

            return False

        for state in states:
            if source_state['found']:
                results.append(state_to_dict(state))
            else:
                if state.merge_state == 1:
                    # state is a new record with no parents
                    results.append(state_to_dict(state))
                else:
                    # Look through parents in the audit log to rule out the view that inherited from the initial state
                    audit_merge = audit_log.objects.filter(
                        state_id=state.id,
                        name__in=['Manual Match', 'System Match']
                    ).order_by('-id').first()

                    if not check_audit_merge_history(audit_merge):
                        results.append(state_to_dict(state))

        return {
            'status': 'success',
            'states': results
        }

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
        audit_log = PropertyAuditLog if inventory_type == 'properties' else TaxLotAuditLog
        state_model = PropertyState if inventory_type == 'properties' else TaxLotState
        audit_creation_id = audit_log.objects.only('id').exclude(import_filename=None).get(
            state_id=state_id,
            name='Import Creation'
        ).id
        merged_record = audit_log.objects.only('parent_state1_id', 'parent_state2_id').filter(
            Q(parent1_id=audit_creation_id) | Q(parent2_id=audit_creation_id))

        if not merged_record.exists():
            return False

        if merged_record.count() > 1:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Internal problem occurred, more than one merge record found'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        audit_entry = merged_record.first()
        state_id1 = audit_entry.parent_state1_id

        # check if we are returning as subset of the fields (as values)
        if fields:
            if state_id1 != state_id:
                return state_model.objects.filter(id=audit_entry.parent_state1_id).values(*fields)[
                    0]
            else:
                return state_model.objects.filter(id=audit_entry.parent_state2_id).values(*fields)[
                    0]
        else:
            return audit_entry.parent_state1 if state_id1 != state_id else audit_entry.parent_state2

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
        coparent = self.has_coparent(source_state_id, inventory_type)
        if not coparent:
            return JsonResponse({
                'status': 'error',
                'message': 'Source state is already unmatched'
            }, status=status.HTTP_400_BAD_REQUEST)

        if coparent.id != coparent_id:
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

        state1 = coparent
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
    @detail_route(methods=['GET'], url_path='data_quality_results_csv')
    def get_csv(self, request, pk=None):
        """
        Download a csv of the results.
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

        import_file_id = pk
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(import_file_id))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Data Quality Check Results.csv"'

        writer = csv.writer(response)
        if data_quality_results is None:
            writer.writerow(['Error'])
            writer.writerow(['data quality results not found'])
            return response

        writer.writerow(
            ['Table', 'Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
             'Error Message', 'Severity'])

        for row in data_quality_results:
            for result in row['data_quality_results']:
                writer.writerow([
                    row['data_quality_results'][0]['table_name'],
                    row['address_line_1'],
                    row['pm_property_id'] if 'pm_property_id' in row else None,
                    row['jurisdiction_tax_lot_id'] if 'jurisdiction_tax_lot_id' in row else None,
                    row['custom_id_1'],
                    result['formatted_field'],
                    result['detailed_message'],
                    result['severity']
                ])

        return response

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
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'gfa',
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
        status1 = Column.create_mappings(mappings, organization, request.user)

        # extract the to_table_name and to_field
        column_mappings = [
            {'from_field': m['from_field'],
             'to_field': m['to_field'],
             'to_table_name': m['to_table_name']} for m in mappings]
        if status1:
            import_file.save_cached_mapped_columns(column_mappings)
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
        a given ImportFile record.

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
        # If a record was manually edited then remove the edited version
        properties_to_remove = list()
        for p in properties:
            if PropertyAuditLog.objects.filter(
                state_id=p.id,
                name='Manual Edit'
            ).exists():
                properties_to_remove.append(p.id)
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
        taxlots_to_remove = list()
        for t in taxlots:
            if TaxLotAuditLog.objects.filter(
                state_id=t.id,
                name='Manual Edit'
            ).exists():
                taxlots_to_remove.append(t.id)
        taxlots = [t for t in taxlots if t.id not in taxlots_to_remove]

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
                'matched_ids': properties_matched,
                'unmatched': len(properties_new),
                'unmatched_ids': properties_new
            },
            'tax_lots': {
                'matched': len(tax_lots_matched),
                'matched_ids': tax_lots_matched,
                'unmatched': len(tax_lots_new),
                'unmatched_ids': tax_lots_new
            }
        }

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
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
        org_id = request.query_params.get('organization_id', None)

        result = _mapping_suggestions(pk, org_id, request.user)

        return JsonResponse(result)
