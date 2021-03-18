# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
import logging
import os
import pprint
import time

import psutil
import requests
import urllib3
from http.client import RemoteDisconnected


def report_memory():
    mem = psutil.virtual_memory()
    print(mem)
    print(f'Free mem (MB): {mem.available / 1024}')
    min_amount = 100 * 1024 * 1024  # 100MB
    if mem.available <= min_amount:
        print("WARNING: Memory is low on system")

    # also report the processes (that we care about)
    ps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'python' in p.info['name']]
    print(f'Python processes: {ps}')
    ps = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'celery' in p.info['name']]
    print(f'Celery processes: {ps}')


# Three-step upload process
def upload_file(upload_header, organization_id, upload_filepath, main_url, upload_dataset_id, upload_datatype):
    """
    Proceeds with the filesystem upload.

    Args:
        upload_header: GET request headers
        upload_filepath: full path to file
        main_url: Host
        upload_dataset_id: What ImportRecord to associate file with.
        upload_datatype: Type of data in file (Assessed Raw, Portfolio Raw)

    Returns:
        {
            "import_file_id": 54,
            "success": true,
            "filename": "DataforSEED_dos15.csv"
        }
    """
    upload_url = "%s/api/v3/upload/?organization_id=%s" % (main_url, organization_id)
    params = {
        'qqfile': upload_filepath,
        'import_record': upload_dataset_id,
        'source_type': upload_datatype
    }
    return requests.post(upload_url,
                         params=params,
                         files={'file': open(upload_filepath, 'rb')},
                         headers=upload_header)


def check_status(result_out, part_msg, log, piid_flag=None):
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    passed = '\033[1;32m...passed\033[1;0m'
    failed = '\033[1;31m...failed\033[1;0m'

    if result_out.status_code in [200, 201, 403, 401]:
        try:
            if piid_flag == 'export':
                content_str = result_out.content.decode()
                if content_str.startswith('id'):
                    msg = "Data exported successfully"
                    # the data are returned as text. No easy way to check the status. If ID
                    # exists, then claim success.
                else:
                    msg = content_str
            elif 'status' in result_out.json() and result_out.json()['status'] == 'error':
                msg = result_out.json()['message']
                log.error(part_msg + failed)
                log.debug(msg)
                raise RuntimeError
            elif 'success' in result_out.json() and not result_out.json()['success']:
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
                else:
                    msg = pprint.pformat(result_out.json(), indent=2, width=70)
        except BaseException:
            log.error(part_msg + failed)
            log.debug('Unknown error during request results recovery')
            raise RuntimeError

        log.info(part_msg + passed)
        log.debug(msg)

    elif result_out.status_code in [204]:
        msg = result_out.content
        log.info(part_msg + passed)
        log.debug(msg)

    else:
        msg = result_out.reason
        log.error(part_msg + failed)
        log.debug(msg)
        raise RuntimeError

    return


def check_progress(main_url, header, progress_key):
    """Delays the sequence until progress is at 100 percent."""
    time.sleep(2)
    print("checking progress {}".format(progress_key))
    try:
        progress_result = requests.get(
            main_url + '/api/v3/progress/{}/'.format(progress_key),
            headers=header
        )
        print("... {} ...".format(progress_result.json()['progress']))
    except [urllib3.exceptions.ProtocolError, RemoteDisconnected, requests.exceptions.ConnectionError]:
        print("Server is not responding... trying again in a few seconds")
        progress_result = None
    except Exception:
        print("Other unknown exception caught!")
        progress_result = None

    if progress_result and progress_result.json()['progress'] == 100:
        return progress_result
    else:
        progress_result = check_progress(main_url, header, progress_key)

    return progress_result


def read_map_file(mapfile_path):
    """Read in the mapping file"""

    assert (os.path.isfile(mapfile_path)), "Cannot find file:\t" + mapfile_path

    map_reader = csv.reader(open(mapfile_path, 'r'))
    map_reader.__next__()  # Skip the header

    # Open the mapping file and fill list
    maplist = list()

    for rowitem in map_reader:
        maplist.append(
            {
                'from_field': rowitem[0],
                'from_units': rowitem[1],
                'to_table_name': rowitem[2],
                'to_field': rowitem[3],
            }
        )

    return maplist


def setup_logger(filename, write_file=True):
    """Set-up the logger object"""

    logging.getLogger("requests").setLevel(logging.WARNING)

    _log = logging.getLogger()
    _log.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    formatter_console = logging.Formatter('%(levelname)s - %(message)s')

    if write_file:
        fh = logging.FileHandler(filename, mode='a')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        _log.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter_console)
    _log.addHandler(ch)

    return _log


def write_out_django_debug(partmsg, result):
    if result.status_code != 200:
        filename = '{}_fail.html'.format(partmsg)
        with open(filename, 'w') as fail:
            fail.writelines(result.text)
        print('Wrote debug -> {}'.format(filename))
