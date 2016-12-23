# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import base64
import hashlib
import hmac
import json
import logging
import os

from ajaxuploader.backends.local import LocalUploadBackend
from ajaxuploader.views import AjaxFileUploader
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from rest_framework.decorators import api_view

from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
)
from seed.decorators import ajax_request, ajax_request_class
from seed.utils.api import api_endpoint, api_endpoint_class
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets
from rest_framework.decorators import parser_classes

from django.core.files.storage import FileSystemStorage

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
    _log.info("Created ImportFile. kw_fields={} from-PM={}"
              .format(kw_fields, f.from_portfolio_manager))
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
        with open(path, 'wb+') as temp_file:
            for chunk in the_file.chunks():
                temp_file.write(chunk)

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
                                      file=path,
                                      source_type=source_type,
                                      **kw_fields)

        _log.info("Created ImportFile. kw_fields={} from-PM={}"
                  .format(kw_fields, f.from_portfolio_manager))

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
