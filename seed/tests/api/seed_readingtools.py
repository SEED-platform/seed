# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import pprint
import json
import os
import requests
import csv
import datetime as dt
import time
from calendar import timegm

# Three-step upload process
def upload_file(upload_header, upload_filepath, main_url, upload_dataset_id, upload_datatype):
    """
    Checks if the upload is through an AWS system or through filesystem.
    Proceeds with the appropriate upload method.

    - uploadFilepath: full path to file
    - uploadDatasetID: What ImportRecord to associate file with.
    - uploadDatatype: Type of data in file (Assessed Raw, Portfolio Raw)
    """

    def _upload_file_to_aws(aws_upload_details):
        """
        This code is from the original APIClient.
        Implements uploading a data file to S3 directly.
        This is a 3-step process:
        1. SEED instance signs the upload request.
        2. File is uploaded to S3 with signature included.
        3. Client notifies SEED instance when upload completed.
        @TODO: Currently can only upload to s3.amazonaws.com, though there are
            other S3-compatible services that could be drop-in replacements.

        Args:
        - AWSuploadDetails: Results from 'get_upload_details' endpoint;
            contains details about where to send file and how.

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
        """
        # Step 1: get the request signed
        sig_uri = aws_upload_details['signature']

        now = dt.datetime.utcnow()
        expires = now + dt.timedelta(hours=1)
        now_ts = timegm(now.timetuple())
        key = 'data_imports/%s.%s' % (filename, now_ts)

        payload = {}
        payload['expiration'] = expires.isoformat() + 'Z'
        payload['conditions'] = [
            {'bucket': aws_upload_details['aws_bucket_name']},
            {'Content-Type': 'text/csv'},
            {'acl': 'private'},
            {'success_action_status': '200'},
            {'key': key}
        ]

        sig_result = requests.post(main_url + sig_uri,
                                   headers=upload_header,
                                   data=json.dumps(payload))
        if sig_result.status_code != 200:
            msg = "Something went wrong with signing document."
            raise RuntimeError(msg)
        else:
            sig_result = sig_result.json()

        # Step 2: upload the file to S3
        upload_url = "http://%s.s3.amazonaws.com/" % (aws_upload_details['aws_bucket_name'])

        # s3 expects multipart form encoding with files at the end, so this
        # payload needs to be a list of tuples; the requests library will encode
        # it property if sent as the 'files' parameter.
        s3_payload = [
            ('key', key),
            ('AWSAccessKeyId', aws_upload_details['aws_client_key']),
            ('Content-Type', 'text/csv'),
            ('success_action_status', '200'),
            ('acl', 'private'),
            ('policy', sig_result['policy']),
            ('signature', sig_result['signature']),
            ('file', (filename, open(upload_filepath, 'rb')))
        ]

        result = requests.post(upload_url,
                               files=s3_payload)

        if result.status_code != 200:
            msg = "Something went wrong with the S3 upload: %s " % result.reason
            raise RuntimeError(msg)

        # Step 3: Notify SEED about the upload
        completion_uri = aws_upload_details['upload_complete']
        completion_payload = {
            'import_record': upload_dataset_id,
            'key': key,
            'source_type': upload_datatype
        }
        return requests.get(main_url + completion_uri,
                            headers=upload_header,
                            params=completion_payload)

    def _upload_file_to_file_system(upload_details):
        """
        Implements uploading to SEED's filesystem. Used by
        upload_file if SEED in configured for local file storage.

        Args:
            FSYSuploadDetails: Results from 'get_upload_details' endpoint;
                contains details about where to send file and how.

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
        """
        upload_url = "%s%s" % (main_url, upload_details['upload_path'])
        fsysparams = {'qqfile': upload_filepath,
                      'import_record': upload_dataset_id,
                      'source_type': upload_datatype}
        return requests.post(upload_url,
                             params=fsysparams,
                             files={'filename': open(upload_filepath, 'rb')},
                             headers=upload_header)

    # Get the upload details.
    upload_details = requests.get(main_url + '/data/get_upload_details/', headers=upload_header)
    upload_details = upload_details.json()

    filename = os.path.basename(upload_filepath)

    if upload_details['upload_mode'] == 'S3':
        return _upload_file_to_aws(upload_details)
    elif upload_details['upload_mode'] == 'filesystem':
        return _upload_file_to_file_system(upload_details)
    else:
        raise RuntimeError("Upload mode unknown: %s" %
                           upload_details['upload_mode'])

def check_status(resultOut, partmsg, log, PIIDflag=None):
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    if resultOut.status_code in [200, 403, 401]:
        if PIIDflag == 'cleansing':
            msg = pprint.pformat(resultOut.json(), indent=2, width=70)
        else:
            try:
                if 'status' in resultOut.json().keys() and resultOut.json()['status'] == 'error':
                    msg = resultOut.json()['message']
                    log.error(partmsg+'...not passed')
                    log.debug(msg)
                    raise RuntimeError
                elif 'success' in resultOut.json().keys() and resultOut.json()['success'] == False:
                    msg = resultOut.json()
                    log.error(partmsg+'...not passed')
                    log.debug(msg)
                    raise RuntimeError
                else:
                    if PIIDflag == 'organizations':
                        msg = 'Number of organizations:\t' + str(len(resultOut.json()['organizations'][0]))
                    elif PIIDflag == 'users':
                        msg = 'Number of users:\t' + str(len(resultOut.json()['users'][0]))
                    elif PIIDflag == 'mappings':
                        msg = pprint.pformat(resultOut.json()['suggested_column_mappings'], indent=2, width=70)
                    elif PIIDflag == 'PM_filter':
                        msg = "Duplicates: " + str(resultOut.json()['duplicates']) + ", Unmatched: " + str(resultOut.json()['unmatched']) + ", Matched: " + str(resultOut.json()['matched'])
                    else:
                        msg = pprint.pformat(resultOut.json(), indent=2, width=70)
            except:
                log.error(partmsg,'...not passed')
                log.debug('Unknown error during request results recovery')
                raise RuntimeError

        log.info(partmsg+'...passed')
        log.debug(msg)
    else:
        msg = resultOut.reason
        log.error(partmsg+'...not passed')
        log.debug(msg)
        raise RuntimeError

    return

def check_progress(mainURL, Header, progress_key):
    """Delays the sequence until progress is at 100 percent."""
    time.sleep(5)
    progressResult = requests.get(mainURL+'/app/progress/',
                       headers = Header,
                       data = json.dumps({'progress_key':progress_key}))

    if progressResult.json()['progress'] == 100:
        return (progressResult)
    else:
        progressResult = check_progress(mainURL, Header, progress_key)

def read_map_file(mapfilePath):
    """Read in the mapping file"""

    assert (os.path.isfile(mapfilePath)),"Cannot find file:\t"+mapfilePath

    mapReader = csv.reader(open(mapfilePath,'r'))
    mapReader.next()    #Skip the header

    # Open the mapping file and fill list
    maplist = list()

    for rowitem in mapReader:
        maplist.append(rowitem)

    return maplist

def setup_logger(filename):
    """Set-up the logger object"""

    logging.getLogger("requests").setLevel(logging.WARNING)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    formatter_console = logging.Formatter('%(levelname)s - %(message)s')

    fh = logging.FileHandler(filename, mode='a')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter_console)
    logger.addHandler(ch)

    return logger
