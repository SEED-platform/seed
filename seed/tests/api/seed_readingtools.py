﻿# !/usr/bin/env python
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
    Checks if the upload is through an AWS system or through file system.
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
        return requests.post(main_url + completion_uri,
                             headers=upload_header,
                             data=completion_payload)

    def _upload_file_to_file_system(upload_details):
        """
        Implements uploading to SEED's file system. Used by
        upload_file if SEED in configured for local file storage.

        Args:
            FSYSuploadDetails: Results from 'get_upload_details' endpoint;
                contains details about where to send file and how.

        Returns:
            {
                "import_file_id": 54,
                "success": true,
                "filename": "DataforSEED_dos15.csv"
            }
        """
        upload_url = "%s%s" % (main_url, upload_details['upload_path'])
        fsysparams = {
            'qqfile': upload_filepath,
            'import_record': upload_dataset_id,
            'source_type': upload_datatype
        }

        print upload_url
        return requests.post(upload_url,
                             params=fsysparams,
                             files={'filename': open(upload_filepath, 'rb')},
                             headers=upload_header)

    # Get the upload details.
    upload_details = requests.get(main_url + '/api/v2/get_upload_details/',
                                  headers=upload_header)
    upload_details = upload_details.json()

    filename = os.path.basename(upload_filepath)

    if upload_details['upload_mode'] == 'S3':
        return _upload_file_to_aws(upload_details)
    elif upload_details['upload_mode'] == 'filesystem':
        print upload_details
        return _upload_file_to_file_system(upload_details)
    else:
        raise RuntimeError("Upload mode unknown: %s" %
                           upload_details['upload_mode'])


def cycles(header, main_url, organization_id, log):
    print ('API Function: get_cycles\n')
    partmsg = 'get_cycles'
    try:
        result = requests.get(main_url + '/app/get_cycles/',
                              headers=header,
                              params={'organization_id': organization_id})
        print result
        check_status(result, partmsg, log, PIIDflag='cycles')

        cycles = result.json()['cycles']
        print "current cycles are {}".format(cycles)
        for cyc in cycles:
            if cyc['name'] == 'TestCycle':
                cycle_id = cyc['id']
                break
        else:
            # Create cycle (only if it doesn't exist, until there is a function to delete cycles)
            print ('API Function: create_cycle\n')
            partmsg = 'create_cycle'
            payload = {
                'start': "2015-01-01T08:00:00.000Z",
                'end': "2016-01-01T08:00:00.000Z",
                'name': "TestCycle"
            }
            result = requests.post(main_url + '/app/create_cycle/',
                                   headers=header,
                                   params={'organization_id': organization_id},
                                   data=json.dumps(payload))
            check_status(result, partmsg, log)

            cycles = result.json()['cycles']
            for cyc in cycles:
                if cyc['name'] == 'TestCycle':
                    cycle_id = cyc['id']
                    break
    except:
        cycle_id = 138

    # Update cycle
    print ('\nAPI Function: update_cycle')
    partmsg = 'update_cycle'
    print cycle_id
    payload = {
        'start': "2015-01-01T08:00:00.000Z",
        'end': "2016-01-01T08:00:00.000Z",
        'name': "TestCycle",
        'id': cycle_id
    }
    result = requests.put(main_url + '/app/update_cycle/',
                          headers=header,
                          params={'organization_id': organization_id},
                          data=json.dumps(payload))
    check_status(result, partmsg, log)

    return cycle_id


def check_status(result_out, part_msg, log, piid_flag=None):
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    passed = '\033[1;32m...passed\033[1;0m'
    failed = '\033[1;31m...failed\033[1;0m'

    if result_out.status_code in [200, 403, 401]:
        if piid_flag == 'cleansing':
            msg = pprint.pformat(result_out.json(), indent=2, width=70)
        else:
            try:
                if 'status' in result_out.json().keys() and result_out.json()['status'] == 'error':
                    msg = result_out.json()['message']
                    log.error(part_msg + failed)
                    log.debug(msg)
                    raise RuntimeError
                elif 'success' in result_out.json().keys() and not result_out.json()['success']:
                    msg = result_out.json()
                    log.error(part_msg + failed)
                    log.debug(msg)
                    raise RuntimeError
                else:
                    if piid_flag == 'organizations':
                        msg = 'Number of organizations:\t' + str(
                            len(result_out.json()['organizations'][0]))
                    elif piid_flag == 'users':
                        msg = 'Number of users:\t' + str(len(result_out.json()['users'][0]))
                    elif piid_flag == 'mappings':
                        msg = pprint.pformat(result_out.json()['suggested_column_mappings'],
                                             indent=2, width=70)
                    elif piid_flag == 'PM_filter':
                        msg = "Duplicates: " + str(
                            result_out.json()['duplicates']) + ", Unmatched: " + str(
                            result_out.json()['unmatched']) + ", Matched: " + str(
                            result_out.json()['matched'])
                    else:
                        msg = pprint.pformat(result_out.json(), indent=2, width=70)
            except:
                log.error(part_msg + failed)
                log.debug('Unknown error during request results recovery')
                raise RuntimeError

        log.info(part_msg + passed)
        log.debug(msg)
    else:
        msg = result_out.reason
        print msg.json
        log.error(part_msg + failed)
        log.debug(msg)
        raise RuntimeError

    return


def check_progress(mainURL, Header, progress_key):
    """Delays the sequence until progress is at 100 percent."""
    time.sleep(5)
    progressResult = requests.post(mainURL + '/api/v2/progress/',
                                   headers=Header,
                                   data=json.dumps({'progress_key': progress_key}))

    if progressResult.json()['progress'] == 100:
        return (progressResult)
    else:
        progressResult = check_progress(mainURL, Header, progress_key)


def read_map_file(mapfilePath):
    """Read in the mapping file"""

    assert (os.path.isfile(mapfilePath)), "Cannot find file:\t" + mapfilePath

    mapReader = csv.reader(open(mapfilePath, 'r'))
    mapReader.next()  # Skip the header

    # Open the mapping file and fill list
    maplist = list()

    for rowitem in mapReader:
        # formerly
        # maplist.append(rowitem)
        # changed to make the test pass
        maplist.append(
            {
                'to_table_name': rowitem[0], 'to_field': rowitem[1],
                # rowitem only has 2 values, lets make this one up
                'from_field': rowitem[0]
            }
        )
    return maplist


def setup_logger(filename, write_file=True):
    """Set-up the logger object"""

    logging.getLogger("requests").setLevel(logging.WARNING)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    formatter_console = logging.Formatter('%(levelname)s - %(message)s')

    if write_file:
        fh = logging.FileHandler(filename, mode='a')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter_console)
    logger.addHandler(ch)

    return logger


def write_out_django_debug(partmsg, result):
    if result.status_code != 200:
        filename = '{}_fail.html'.format(partmsg)
        with open(filename, 'w') as fail:
            fail.writelines(result.text)
        print 'Wrote debug -> {}'.format(filename)
