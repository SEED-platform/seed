# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import base64
import json
import hmac
import hashlib
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from ajaxuploader.views import AjaxFileUploader
from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
)
from seed.decorators import ajax_request
from ajaxuploader.backends.local import LocalUploadBackend
from seed.utils.api import api_endpoint
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured

_log = logging.getLogger(__name__)

@api_endpoint
@ajax_request
@login_required
def handle_s3_upload_complete(request):
    """
    Notify the system that an upload to S3 has been completed. This is
    a necessary step after uploading to S3 or the SEED instance will not
    be aware the file exists.

    Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

    :GET: Expects the following in the query string:

        key: The full path to the file, within the S3 bucket.
            E.g. data_importer/bldgs.csv

        source_type: The source of the file.
            E.g. 'Assessed Raw' or 'Portfolio Raw'

        source_program: Optional value from common.mapper.Programs
        source_version: e.g. "4.1"

        import_record: The ID of the ImportRecord this file belongs to.

    Returns::

        {'success': True,
         'import_file_id': The ID of the newly-created ImportFile object.
        }
    """
    if 'S3' not in settings.DEFAULT_FILE_STORAGE:
        return {'success': False,
                'message': "Direct-to-S3 uploads not enabled"}

    import_record_pk = request.REQUEST['import_record']
    try:
        record = ImportRecord.objects.get(pk=import_record_pk)
    except ImportRecord.DoesNotExist:
        #TODO: Remove the file from S3?
        return {'success': False,
                'message': "Import Record %s not found" % import_record_pk}

    filename = request.REQUEST['key']
    source_type = request.REQUEST['source_type']
    # Add Program & Version fields (empty string if not given)
    kw_fields = {field:request.REQUEST.get(field, '')
        for field in ['source_program', 'source_program_version']}

    f = ImportFile.objects.create(import_record=record,
                                  file=filename,
                                  source_type=source_type,
                                  **kw_fields)
    _log.info("Created ImportFile. kw_fields={} from-PM={}"
              .format(kw_fields, f.from_portfolio_manager))
    return {'success': True, "import_file_id": f.pk}


class DataImportBackend(LocalUploadBackend):
    """
    Subclass of ajaxuploader's LocalUploadBackend, to handle
    creation of ImportFile objects related to the specified
    ImportRecord.
    """

    def upload_complete(self, request, filename, *args, **kwargs):
        """
        Called directly by fineuploader on upload completion.
        """
        if 'S3' in settings.DEFAULT_FILE_STORAGE:
            os.unlink(self.path)
            raise ImproperlyConfigured("Local upload not supported")

        super(DataImportBackend, self).upload_complete(
            request, filename, *args, **kwargs
        )

        import_record_pk = request.REQUEST['import_record']
        try:
            record = ImportRecord.objects.get(pk=import_record_pk)
        except ImportRecord.DoesNotExist:
            #clean up the uploaded file
            os.unlink(self.path)
            return {'success': False,
                    'message': "Import Record %s not found" % import_record_pk}

        source_type = request.REQUEST['source_type']

        # Add Program & Version fields (empty string if not given)
        kw_fields = {field: request.REQUEST.get(field, '')
                     for field in ['source_program', 'source_program_version']}

        f = ImportFile.objects.create(import_record=record,
                                      file=self.path,
                                      source_type=source_type,
                                      **kw_fields)

        _log.info("Created ImportFile. kw_fields={} from-PM={}"
                  .format(kw_fields, f.from_portfolio_manager))

        return {'success': True, "import_file_id": f.pk}

#this actually creates the django view for handling local file uploads.
#thus the use of decorators as functions instead of decorators.
local_uploader = AjaxFileUploader(backend=DataImportBackend)
local_uploader = login_required(local_uploader)
local_uploader = api_endpoint(local_uploader)

#API documentation and method name fix
local_uploader.__doc__ = \
"""
Endpoint to upload data files to, if uploading to local file storage.
Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``


:GET:

    The following parameters are expected to be in the query string:

    import_record: the ID of the ImportRecord to associate this file with.

    qqfile: The name of the file

    source_type: A valid source type (e.g. 'Portfolio Raw' or 'Assessed Raw')


Payload::

    The content of the file as a data stream.  Do not use multipart encoding.

Returns::

    {'success': True,
     'import_file_id': The ID of the newly-uploaded ImportFile
    }

"""
local_uploader.__name__ = 'local_uploader'


@api_endpoint
@ajax_request
@login_required
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

        If local filesystem mode:
        {'upload_mode': 'filesystem',
         'upload_path': The url to POST files to (see local_uploader)
        }

    """
    ret = {}
    if 'S3' in settings.DEFAULT_FILE_STORAGE:
        # S3 mode
        ret['upload_mode'] = 'S3'
        ret['upload_complete'] = reverse('data_importer:s3_upload_complete')
        ret['signature'] = reverse('data_importer:sign_policy_document')
        ret['aws_bucket_name'] = settings.AWS_BUCKET_NAME
        ret['aws_client_key'] = settings.AWS_UPLOAD_CLIENT_KEY
    else:
        ret['upload_mode'] = 'filesystem'
        ret['upload_path'] = reverse('data_importer:local_uploader')
    return ret


@api_endpoint
@ajax_request
@login_required
def sign_policy_document(request):
    """
    Sign and return the policy doucument for a simple upload.
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
         "signature": A signature of the policy document.  Also used during
                     upload to S3.

        }
    """
    policy_document = json.loads(request.body)
    policy = base64.b64encode(json.dumps(policy_document))
    signature = base64.b64encode(
        hmac.new(
            settings.AWS_UPLOAD_CLIENT_SECRET_KEY, policy, hashlib.sha1
        ).digest()
    )
    return {
        'policy': policy,
        'signature': signature
    }
