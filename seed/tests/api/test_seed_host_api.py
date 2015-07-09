"""
API Testing for remote SEED installations.
:copyright (c) 2014, The Regents of the University of California, Department of Energy contract-operators of the Lawrence Berkeley National Laboratory.
:author Claudine Custodio
"""

import os
import pprint
import json
import datetime as dt
import time
from calendar import timegm

import requests



# Three-step upload process 
def upload_file(upload_header, upload_filepath, upload_url, upload_dataset_id, upload_datatype):
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

        sig_result = requests.post(upload_url + sig_uri,
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
        return requests.get(upload_url + completion_uri,
                            headers=upload_header,
                            params=completion_payload)

    def _upload_file_to_file_system(upload_url, upload_details):
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
        upload_url = "%s%s" % (upload_url, upload_details['upload_path'])
        fsysparams = {'qqfile': upload_filepath,
                      'import_record': upload_dataset_id,
                      'source_type': upload_datatype}
        return requests.post(upload_url,
                             params=fsysparams,
                             files={'filename': open(upload_filepath, 'rb')},
                             headers=upload_header)

    # Get the upload details.
    upload_details = requests.get(upload_url + '/data/get_upload_details/', headers=upload_header)
    upload_details = upload_details.json()

    filename = os.path.basename(upload_filepath)

    if upload_details['upload_mode'] == 'S3':
        return _upload_file_to_aws(upload_details)
    elif upload_details['upload_mode'] == 'filesystem':
        return _upload_file_to_file_system(upload_url, upload_details)
    else:
        raise RuntimeError("Upload mode unknown: %s" %
                           upload_details['upload_mode'])


def check_status(result_out, file_out, pid_flag=None):
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    if result_out.status_code in [200, 403, 401]:
        if 'status' in result_out.json().keys() and result_out.json()['status'] == 'error':
            print ('...not passed')
            msg = result_out.json()['message']
            pprint.pprint(msg, stream=file_out)
            file_out.close()
            raise RuntimeError(msg)
        elif 'success' in result_out.json().keys() and result_out.json()['success'] == False:
            print ('...not passed')
            msg = result_out.json()
            pprint.pprint(msg, stream=file_out)
            file_out.close()
            raise RuntimeError(msg)
            file_out.close
        else:
            if pid_flag == 'organizations':
                print ('...passed')
                pprint.pprint('Number of organizations:    ' +
                              str(len(result_out.json()['organizations'][0])),
                              stream=file_out)
            elif pid_flag == 'users':
                print ('...passed')
                pprint.pprint('Number of users:    ' +
                              str(len(result_out.json()['users'][0])),
                              stream=file_out)
            else:
                print ('...passed')
                pprint.pprint(result_out.json(), stream=file_out)
    else:
        print ('...not passed')
        msg = result_out.reason
        pprint.pprint(msg, stream=file_out)
        file_out.close()
        raise RuntimeError(msg)
        file_out.close
    return

# ---
# Set up the request credentials
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

# Set up output file
fileout = open(hostname + '_seedhost.txt', 'w')
fileout.write('Hostname: \t' + hostname)
fileout.write('\nURL: \t\t' + main_url)
fileout.write('\nTest Date:\t' + dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S'))

# -- Accounts
print ('\n-------Accounts-------\n')
fileout.write('\n-------Accounts-------\n')
# Retrieve the user profile 
print ('API Function: get_user_profile'),
fileout.write('API Function: get_user_profile\n')
result = requests.get(main_url + '/app/accounts/get_user_profile', headers=header)
check_status(result, fileout)

# Retrieve the organizations 
print ('API Function: get_organizations'),
fileout.write('API Function: get_organizations\n')
result = requests.get(main_url + '/app/accounts/get_organizations/',
                      headers=header)
# TODO Return number of organizations 
check_status(result, fileout, pid_flag='organizations')

# # Get the organization id to be used.
# # NOTE: Loop through the organizations and get the org_id 
# # where the organization owner is 'Username' else get the first organization. 
orgs_result = result.json()
for ctr in range(len(orgs_result['organizations'])):
    if orgs_result['organizations'][ctr]['owners'][0]['email'] == username:
        organization_id = orgs_result['organizations'][ctr]['org_id']
        break
    else:
        organization_id = orgs_result['organizations'][0]['org_id']

# Get the organization details 
print ('API Function: get_organization'),
fileout.write('API Function: get_organization\n')
mod_url = main_url + '/app/accounts/get_organization/?organization_id=' + str(organization_id)
result = requests.get(mod_url, headers=header)
check_status(result, fileout)

# Change user profile
# NOTE: Make sure these credentials are ok.
print ('API Function: update_user'),
fileout.write('API Function: update_user\n')
user_payload = {'user': {'first_name': 'C',
                         'last_name': 'Custodio',
                         'email': username}}
result = requests.post(main_url + '/app/accounts/update_user/',
                       headers=header,
                       data=json.dumps(user_payload))
check_status(result, fileout)

# # Create a user 
# print ('API Function: add_user'),
# fileout.write ('API Function: add_user\n')
# newuser_payload = {'organization_id': organizationID,
# 'first_name': 'C1_owner',
# 'last_name': 'Cust',
# 'role': {'name':'Member',
# 'value': 'member'},
# 'email': 'cycustodio+1@lbl.gov' }
# result = requests.post(mainURL+'/app/accounts/add_user/',
# headers=Header,
# data=json.dumps(newuser_payload))
# check_status(result, fileout)

# Get organization users
print ('API Function: get_organizations_users'),
fileout.write('API Function: get_organizations_users\n')
org_payload = {'organization_id': organization_id}
result = requests.post(main_url + '/app/accounts/get_organizations_users/',
                       headers=header,
                       data=json.dumps(org_payload))
check_status(result, fileout, pid_flag='users')

# # Get the new user id 
# newuser = result.json()
# newuserID = newuser['users'][1]['user_id']

# # Change the user role 
# print ('API Function: update_role'),
# fileout.write ('API Function: update_role\n')
# newrole_payload = {'organization_id': organizationID,
# 'user_id': newuserID,
# 'role': 'member' }
# result = requests.post(mainURL+'/app/accounts/update_role/',
# headers=Header,
# data=json.dumps(newrole_payload))
# check_status(result, fileout)

# Get organizations settings
print ('API Function: get_query_threshold'),
fileout.write('API Function: get_query_threshold\n')
result = requests.get(main_url + '/app/accounts/get_query_threshold/',
                      headers=header,
                      params={'organization_id': organization_id})
check_status(result, fileout)

print ('API Function: get_shared_fields'),
fileout.write('API Function: get_shared_fields\n')
result = requests.get(main_url + '/app/accounts/get_shared_fields/',
                      headers=header,
                      params={'organization_id': organization_id})
check_status(result, fileout)

# -- Dataset
print ('\n-------Dataset-------\n')
fileout.write('\n-------Dataset-------\n')
# Set up directory for file uploads
sample_dir = "data"

# Load raw files. 
raw_building_file = os.path.relpath(os.path.join(sample_dir, 'covered-buildings-sample.csv'))
assert (os.path.isfile(raw_building_file)), 'Missing file ' + raw_building_file

pm_building_file = os.path.relpath(os.path.join(sample_dir, 'portfolio-manager-sample.csv'))
assert (os.path.isfile(pm_building_file)), "Missing file " + pm_building_file

# Create a dataset 
print ('API Function: create_dataset'),
fileout.write('API Function: create_dataset\n')
payload = {'organization_id': organization_id,
           'name': 'API Test'}
result = requests.post(main_url + '/app/create_dataset/', headers=header, data=json.dumps(payload))
check_status(result, fileout)

# Get the dataset id to be used 
datasetID = result.json()['id']

print ('\n|---Covered Building File---|\n')
fileout.write('\n|---Covered Building File---|\n')
# Upload the covered-buildings-sample file 
print ('API Function: upload_file'),
fileout.write('API Function: upload_file\n')
result = upload_file(header, raw_building_file, main_url, datasetID, 'Assessed Raw')
check_status(result, fileout)

# Get import ID 
import_id = result.json()['import_file_id']

# Save the data to BuildingSnapshots
print ('API Function: save_raw_data'),
fileout.write('API Function: save_raw_data\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.post(main_url + '/app/save_raw_data/',
                       headers=header,
                       data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

# Save the column mappings. 
print ('API Function: save_column_mappings'),
fileout.write('API Function: save_column_mappings\n')
payload = {'import_file_id': import_id,
           'organization_id': organization_id}
payload['mappings'] = [[u'city', u'City'],
                       [u'postal_code', u'Zip'],
                       [u'gross_floor_area', u'GBA'],
                       [u'building_count', u'BLDGS'],
                       [u'tax_lot_id', u'UBI'],
                       [u'state_province', u'State'],
                       [u'address_line_1', u'Address'],
                       [u'owner', u'Owner'],
                       [u'use_description', u'Property Type'],
                       [u'year_built', u'AYB_YearBuilt']]
result = requests.get(main_url + '/app/save_column_mappings/',
                      headers=header,
                      data=json.dumps(payload))
check_status(result, fileout)

# Map the buildings with new column mappings.
print ('API Function: remap_buildings'),
fileout.write('API Function: remap_buildings\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.get(main_url + '/app/remap_buildings/',
                      headers=header,
                      data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

# Get the mapping suggestions
print ('API Function: get_column_mapping_suggestions'),
fileout.write('API Function: get_column_mapping_suggestions\n')
payload = {'import_file_id': import_id,
           'org_id': organization_id}
result = requests.get(main_url + '/app/get_column_mapping_suggestions/',
                      headers=header,
                      data=json.dumps(payload))
if result.status_code == 200:
    print('...passed')
    pprint.pprint(result.json()['suggested_column_mappings'], stream=fileout)
else:
    print('...not passed')
    pprint.pprint(result.reason, stream=fileout)

# Match uploaded buildings with buildings already in the organization.
print ('API Function: start_system_matching'),
fileout.write('API Function: start_system_matching\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.post(main_url + '/app/start_system_matching/',
                       headers=header,
                       data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

print ('\n|---Portfolio Manager File---|\n')
fileout.write('\n|---Portfolio Manager File---|\n')
# Upload the portfolio-manager-sample file.
print ('API Function: upload_file'),
fileout.write('API Function: upload_file\n')
result = upload_file(header,
                     pm_building_file,
                     main_url,
                     datasetID,
                     'Portfolio Raw')
check_status(result, fileout)

# Get import ID 
import_id = result.json()['import_file_id']

# Save the data to BuildingSnapshots
print ('API Function: save_raw_data'),
fileout.write('API Function: save_raw_data\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.post(main_url + '/app/save_raw_data/',
                       headers=header,
                       data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

# Save the column mappings. 
print ('API Function: save_column_mappings'),
fileout.write('API Function: save_column_mappings\n')
payload = {'import_file_id': import_id,
           'organization_id': organization_id}
payload['mappings'] = [[u'city', u'City'],
                       [u'energy_score', u'ENERGY STAR Score'],
                       [u'state_province', u'State/Province'],
                       [u'site_eui', u'Site EUI (kBtu/ft2)'],
                       [u'year_ending', u'Year Ending'],
                       [u'source_eui_weather_normalized', 'Weather Normalized Source EUI (kBtu/ft2)'],
                       [u'Parking - Gross Floor Area', u'Parking - Gross Floor Area (ft2)'],
                       [u'address_line_1', u'Address 1'],
                       [u'Portfolio Manager Property ID', u'Property Id'],
                       [u'address_line_2', u'Address 2'],
                       [u'source_eui', u'Source EUI (kBtu/ft2)'],
                       [u'release_date', u'Release Date'],
                       [u'National Median Source EUI', u'National Median Source EUI (kBtu/ft2)'],
                       [u'site_eui_weather_normalized', u'Weather Normalized Site EUI (kBtu/ft2)'],
                       [u'National Median Site EUI', u'National Median Site EUI (kBtu/ft2)'],
                       [u'year_built', u'Year Built'],
                       [u'postal_code', u'Postal Code'],
                       [u'owner', u'Organization'],
                       [u'property_name', u'Property Name'],
                       [u'Property Floor Area (Buildings and Parking)',
                        u'Property Floor Area (Buildings and Parking) (ft2)'],
                       [u'Total GHG Emissions', u'Total GHG Emissions (MtCO2e)'],
                       [u'generation_date', u'Generation Date']]
result = requests.get(main_url + '/app/save_column_mappings/',
                      headers=header,
                      data=json.dumps(payload))
check_status(result, fileout)

# Map the buildings with new column mappings.
print ('API Function: remap_buildings'),
fileout.write('API Function: remap_buildings\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.get(main_url + '/app/remap_buildings/',
                      headers=header,
                      data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

# Get the mapping suggestions
print ('API Function: get_column_mapping_suggestions'),
fileout.write('API Function: get_column_mapping_suggestions\n')
payload = {'import_file_id': import_id,
           'org_id': organization_id}
result = requests.get(main_url + '/app/get_column_mapping_suggestions/',
                      headers=header,
                      data=json.dumps(payload))
if result.status_code == 200:
    print('...passed')
    pprint.pprint(result.json()['suggested_column_mappings'], stream=fileout)
else:
    print('...not passed')
    pprint.pprint(result.reason, stream=fileout)

# Match uploaded buildings with buildings already in the organization.
print ('API Function: start_system_matching'),
fileout.write('API Function: start_system_matching\n')
payload = {'file_id': import_id,
           'organization_id': organization_id}
result = requests.post(main_url + '/app/start_system_matching/',
                       headers=header,
                       data=json.dumps(payload))
check_status(result, fileout)

time.sleep(10)
progress = requests.get(main_url + '/app/progress/',
                        headers=header,
                        data=json.dumps({'progress_key': result.json()['progress_key']}))
pprint.pprint(progress.json(), stream=fileout)

print ('\n'),
fileout.write('\n')
# Check number of matched and unmatched BuildingSnapshots
print ('API Function: get_PM_filter_by_counts'),
fileout.write('API Function: get_PM_filter_by_counts\n')
result = requests.get(main_url + '/app/get_PM_filter_by_counts/',
                      headers=header,
                      params={'import_file_id': import_id})
check_status(result, fileout)

# Search CanonicalBuildings
print ('API Function: search_buildings'),
fileout.write('API Function: search_buildings\n')
search_payload = {'filter_params': {u'address_line_1': u'94734 SE Honeylocust Street'}}
result = requests.get(main_url + '/app/search_buildings/',
                      headers=header,
                      data=json.dumps(search_payload))
check_status(result, fileout)


# -- Project
print ('\n-------Project-------\n')
fileout.write('\n-------Project-------\n')
# Create a Project for 'Condo' in 'use_description'
print ('API Function: create_project'),
fileout.write('API Function: create_project\n')
newproject_payload = {'project': {'name': 'New Project' + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  'compliance_type': 'describe compliance type',
                                  'description': 'project description'},
                      'organization_id': organization_id}
result = requests.post(main_url + '/app/projects/create_project/',
                       headers=header,
                       data=json.dumps(newproject_payload))
check_status(result, fileout)

# Get project slug 
projectSlug = result.json()['project_slug']

# Get the projects for the organization
print ('API Function: get_project'),
fileout.write('API Function: get_project\n')
result = requests.get(main_url + '/app/projects/get_projects/',
                      headers=header,
                      params={'organization_id': organization_id})
check_status(result, fileout)

# Populate project by search buildings result 
print ('API Function: add_buildings_to_project'),
fileout.write('API Function: add_buildings_to_project\n')
projectbldg_payload = {'project': {'status': 'active',
                                   'project_slug': projectSlug,
                                   'slug': projectSlug,
                                   'select_all_checkbox': True,
                                   'selected_buildings': [],
                                   'filter_params': {'use_description': 'CONDO'}},
                       'organization_id': organization_id}
result = requests.post(main_url + '/app/projects/add_buildings_to_project/',
                       headers=header,
                       data=json.dumps(projectbldg_payload))
check_status(result, fileout)

# Get the percent/progress of buildings added to project 
time.sleep(10)
progress = requests.post(main_url + '/app/projects/get_adding_buildings_to_project_status_percentage/',
                         headers=header,
                         data=json.dumps({'project_loading_cache_key': result.json()['project_loading_cache_key']}))
pprint.pprint(progress.json(), stream=fileout)

# -- Labels
print ('\n-------Labels-------\n')
fileout.write('\n-------Labels-------\n')
# Create label
print ('API Function: add_label (test label) '),
fileout.write('API Function: add_label\n')
label_payload = {'label': {'name': 'test label',
                           'color': 'gray'}}
result = requests.post(main_url + '/app/projects/add_label/',
                       headers=header,
                       data=json.dumps(label_payload))
check_status(result, fileout)

# Get labelID
labelID = result.json()['label_id']

# Get organization labels                
print ('API Function: get_labels'),
fileout.write('API Function: get_labels\n')
result = requests.get(main_url + '/app/projects/get_labels/',
                      headers=header)
check_status(result, fileout)

# Apply to buildings that have ENERGY STAR Score > 50
print ('API Function: apply_label'),
fileout.write('API Function: apply_label\n')
payload = {'label': {'id': labelID},
           'project_slug': projectSlug,
           'buildings': [],
           'select_all_checkbox': True,
           'search_params': {'filter_params': {'project__slug': projectSlug}}}
result = requests.post(main_url + '/app/projects/apply_label/',
                       headers=header,
                       data=json.dumps(payload))
check_status(result, fileout)

# -- Export --
print ('\n-------Export-------\n')
fileout.write('\n-------Export-------\n')

print ('API Function: export_buildings'),
fileout.write('API Function: export_buildings\n')
export_payload = {'export_name': 'project_buildings',
                  'export_type': "csv",
                  'select_all_checkbox': True,
                  'filter_params': {'project__slug': projectSlug}}
result = requests.post(main_url + '/app/export_buildings/',
                       headers=header,
                       data=json.dumps(export_payload))
check_status(result, fileout)

# Get exportID
export_id = result.json()['export_id']

time.sleep(15)
progress = requests.post(main_url + '/app/export_buildings/progress/',
                         headers=header,
                         data=json.dumps({'export_id': export_id}))
pprint.pprint(progress.json(), stream=fileout)
time.sleep(15)

print ('API Function: export_buildings_download'),
fileout.write('API Function: export_buildings_download\n')
result = requests.post(main_url + '/app/export_buildings/download/',
                       headers=header,
                       data=json.dumps({'export_id': export_id}))
check_status(result, fileout)

fileout.close()
