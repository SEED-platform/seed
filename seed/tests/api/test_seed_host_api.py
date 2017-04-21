﻿# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Claudine Custodio / Baptiste Ravache
"""
"""
API Testing for remote SEED installations.

Instructions:

- Run this file from the root of the repo.

- Copy seed_API_test.ini.example to seed_API_test.ini and make necessary changes. Don't commit the ini file.

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

import datetime as dt
import os
import sys
import time

import requests

from subprocess import Popen

from seed_readingtools import check_status, setup_logger
from test_modules import upload_match_sort, account, delete_set, search_and_project


location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

if '--standalone' in sys.argv:
    # Open runserver as subprocess because tox doesn't support redirects or
    # job control in commands.
    Popen(['python', os.path.join(location, '..', '..', '..', 'manage.py'), 'runserver'])
    time.sleep(5)

if '--noinput' in sys.argv:
    with open(os.path.join(location, 'seed_API_test.ini'), 'r') as f:
        (hostname, main_url, username, api_key) = f.read().splitlines()
else:
    defaultchoice = raw_input('Use "seed_API_test.ini" credentials? [Y]es or Press Any Key ')

    if defaultchoice.upper() == 'Y':
        with open(os.path.join(location, 'seed_API_test.ini'), 'r') as f:
            (hostname, main_url, username, api_key) = f.read().splitlines()

    else:
        hostname = raw_input('Hostname (default: "localhost"): \t')
        if hostname == '':
            hostname = 'localhost'
        main_url = raw_input('Host URL (default: "http://localhost:8080": \t')
        if main_url == '':
            main_url = 'http://localhost:8000'
        username = raw_input('Username: \t')
        api_key = raw_input('APIKEY: \t')

header = {'authorization': ':'.join([username.lower(), api_key])}
# NOTE: The header only accepts lower case usernames.

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


raw_building_file = os.path.relpath(os.path.join(location, '..', 'data', 'covered-buildings-sample.csv'))
assert (os.path.isfile(raw_building_file)), 'Missing file ' + raw_building_file
raw_map_file = os.path.relpath(os.path.join(location, '..', 'data', 'covered-buildings-mapping.csv'))
assert (os.path.isfile(raw_map_file)), 'Missing file ' + raw_map_file
pm_building_file = os.path.relpath(os.path.join(location, '..', 'data', 'portfolio-manager-sample.csv'))
assert (os.path.isfile(pm_building_file)), 'Missing file ' + pm_building_file
pm_map_file = os.path.relpath(os.path.join(location, '..', 'data', 'portfolio-manager-mapping.csv'))
assert (os.path.isfile(pm_map_file)), 'Missing file ' + pm_map_file

# -- Accounts
print ('\n-------Accounts-------\n')
organization_id = account(header, main_url, username, log)

# Create a dataset
print ('API Function: create_dataset')
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
upload_match_sort(header, main_url, organization_id, dataset_id, raw_building_file, 'Assessed Raw', raw_map_file, log)

# Upload and test the portfolio manager file
print ('\n|---Portfolio Manager File---|\n')
upload_match_sort(header, main_url, organization_id, dataset_id, pm_building_file, 'Portfolio Raw', pm_map_file, log)

# Run search and project tests
project_slug = search_and_project(header, main_url, organization_id, log)

# Delete dataset and building
delete_set(header, main_url, organization_id, dataset_id, project_slug, log)

time2 = dt.datetime.now()
diff = time2 - time1
log.info('Processing Time:{}min, {}sec'.format(diff.seconds / 60, diff.seconds % 60))
