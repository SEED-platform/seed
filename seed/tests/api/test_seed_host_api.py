# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Claudine Custodio / Baptiste Ravache
"""
"""
API Testing for remote SEED installations.

Instructions:

- Run this file from the root of the repo.
- Create the JSON file that the test script uses to run the tests.
    - Run ./manage.py create_test_user_json --username demo@example.com --file ./seed/tests/api/api_test_user.json
    - Or create the seed/tests/api/api_test_user.json with the following data:
        {
          "username": "demo@example.com",
          "host": "http://localhost:8000",
          "api_key": "fa0073715dbecb6dcd6dc31f02eb80fa7c3c16b5",
          "name": "seed_api_test"
        }
- Run the script eg. python seed/tests/api/test_seed_host_api.py

Description:
The script reproduce the different steps that a SEED user would do to upload a building file and portfolio manager file,
map each files, match them, create a project and a label and export a list of buildings.

List of arguments:
The script requires a host name (i.e. output file name), the main URL tested (e.g. https://seed.lbl.gov),
the SEED username and the corresponding API key.
Those information can be listed as follow in the .ini file contained with the script or entered at the beginning of the script.

Outputs:
The script will create a .txt file that contains the log of the test, i.e. the success/failure of each apps test and the results of
some apps.

"""

import base64
import datetime as dt
import json
import os
import sys
import time
from subprocess import Popen

import requests

from seed_readingtools import check_status, setup_logger
from test_modules import cycles, upload_match_sort, account, delete_set

location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
print("Running from {}".format(location))

if '--standalone' in sys.argv:
    # Open runserver as subprocess because tox does not support redirects or
    # job control in commands.
    Popen(['python', os.path.join(location, '..', '..', '..', 'manage.py'), 'runserver'])
    time.sleep(5)

if '--noinput' in sys.argv:
    print("Path to json is: {}".format(os.path.join(location, 'api_test_user.json')))
    with open(os.path.join(location, 'api_test_user.json')) as f:
        j_data = json.load(f)
        hostname = j_data['name']
        main_url = j_data['host']
        username = j_data['username']
        api_key = j_data['api_key']
else:
    defaultchoice = raw_input('Use "api_test_user.json" credentials? [Y]es or Press Any Key ')

    if defaultchoice.upper() == 'Y':
        with open(os.path.join(location, 'api_test_user.json')) as f:
            j_data = json.load(f)
            hostname = j_data['name']
            main_url = j_data['host']
            username = j_data['username']
            api_key = j_data['api_key']
    else:
        hostname = raw_input('Hostname (default: "localhost"): \t')
        if hostname == '':
            hostname = 'localhost'
        main_url = raw_input('Host URL (default: "http://localhost:8080": \t')
        if main_url == '':
            main_url = 'http://localhost:8000'
        username = raw_input('Username: \t')
        api_key = raw_input('APIKEY: \t')


# API is now used basic auth with base64 encoding.
# NOTE: The header only accepts lower case usernames.
auth_string = base64.urlsafe_b64encode(
    '{}:{}'.format(username.lower(), api_key)
)
auth_string = 'Basic {}'.format(auth_string)
header = {
    'Authorization': auth_string,
    # "Content-Type": "application/json"
}

time1 = dt.datetime.now()

fileout_name = hostname + '_seedhost.txt'

if '--nofile' not in sys.argv:
    log = setup_logger(fileout_name)

    # Set up output file
    fileout = open(fileout_name, 'w')
    fileout.write('Hostname: \t' + hostname)
    fileout.write('\nURL: \t\t' + main_url)
    fileout.write('\nTest Date:\t' + dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S'))
    fileout.close()
else:
    log = setup_logger(fileout_name, write_file=False)

raw_building_file = os.path.relpath(
    os.path.join(location, '..', 'data', 'covered-buildings-sample.csv'))
assert (os.path.isfile(raw_building_file)), 'Missing file ' + raw_building_file
raw_map_file = os.path.relpath(
    os.path.join(location, '..', 'data', 'covered-buildings-mapping.csv'))
assert (os.path.isfile(raw_map_file)), 'Missing file ' + raw_map_file
pm_building_file = os.path.relpath(
    os.path.join(location, '..', 'data', 'portfolio-manager-sample.csv'))
assert (os.path.isfile(pm_building_file)), 'Missing file ' + pm_building_file
pm_map_file = os.path.relpath(os.path.join(location, '..', 'data', 'portfolio-manager-mapping.csv'))
assert (os.path.isfile(pm_map_file)), 'Missing file ' + pm_map_file

# -- Accounts
print ('\n|-------Accounts-------|\n')
organization_id = account(header, main_url, username, log)

# -- Cycles
print ('\n\n|-------Cycles-------|')
cycle_id = cycles(header, main_url, organization_id, log)

# Create a dataset
print ('\n\n|-------Create Dateset-------|')
partmsg = 'create_dataset'
payload = {'name': 'API Test'}
result = requests.post(main_url + '/api/v2/datasets/?organization_id=%s' % organization_id,
                       headers=header,
                       data=payload)
check_status(result, partmsg, log)

# Get the dataset id to be used
dataset_id = result.json()['id']

# Upload and test the raw building file
print ('\n|---Covered Building File---|\n')
upload_match_sort(header, main_url, organization_id, dataset_id, cycle_id, raw_building_file,
                  'Assessed Raw',
                  raw_map_file, log)

# Upload and test the portfolio manager file
print ('\n|---Portfolio Manager File---|\n')
# upload_match_sort(header, main_url, organization_id, dataset_id, cycle_id, pm_building_file, 'Portfolio Raw',
#                   pm_map_file, log)

# Delete dataset and building
delete_set(header, main_url, organization_id, dataset_id, log)

time2 = dt.datetime.now()
diff = time2 - time1
log.info('Processing Time:{}min, {}sec'.format(diff.seconds / 60, diff.seconds % 60))

exit(0)
#
