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
def uploadfile(uploadHeader, uploadFilepath, uploadUrl, uploadDatasetID, uploadDatatype):
    """
    Checks if the upload is through an AWS system or through filesystem. 
    Proceeds with the appropriate upload method. 
    
    - uploadFilepath: full path to file
    - uploadDatasetID: What ImportRecord to associate file with.
    - uploadDatatype: Type of data in file (Assessed Raw, Portfolio Raw)
    """
    
    def _uploadfiletoAWS(AWSuploadDetails):
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
        #Step 1: get the request signed
        sig_uri = AWSuploadDetails['signature']

        now = dt.datetime.utcnow()
        expires = now + dt.timedelta(hours=1)
        now_ts = timegm(now.timetuple())
        key = 'data_imports/%s.%s' % (filename, now_ts)

        payload = {}
        payload['expiration'] = expires.isoformat() + 'Z'
        payload['conditions'] = [
            {'bucket': AWSuploadDetails['aws_bucket_name']},
            {'Content-Type': 'text/csv'},
            {'acl': 'private'},
            {'success_action_status': '200'},
            {'key': key}
        ]

        sig_result = requests.post(uploadUrl+sig_uri, 
                                  headers=uploadHeader,
                                  data=json.dumps(payload))
        if sig_result.status_code != 200:
            msg = "Something went wrong with signing document."
            raise RuntimeError(msg)
        else: 
            sig_result = sig_result.json()

        #Step 2: upload the file to S3
        upload_url = "http://%s.s3.amazonaws.com/" % (AWSuploadDetails['aws_bucket_name'])

        #s3 expects multipart form encoding with files at the end, so this
        #payload needs to be a list of tuples; the requests library will encode
        #it property if sent as the 'files' parameter.
        s3_payload = [
            ('key', key),
            ('AWSAccessKeyId', AWSuploadDetails['aws_client_key']),
            ('Content-Type', 'text/csv'),
            ('success_action_status', '200'),
            ('acl', 'private'),
            ('policy', sig_result['policy']),
            ('signature', sig_result['signature']),
            ('file', (filename,open(uploadFilepath, 'rb')))
        ]

        result = requests.post(upload_url, 
                               files=s3_payload)

        if result.status_code != 200:
            msg = "Something went wrong with the S3 upload: %s " % result.reason
            raise RuntimeError(msg)

        #Step 3: Notify SEED about the upload
        completion_uri = AWSuploadDetails['upload_complete']
        completion_payload = {
            'import_record': uploadDatasetID,
            'key': key,
            'source_type': uploadDatatype
        }
        return requests.get(uploadUrl+completion_uri,
                           headers=uploadHeader,
                           params=completion_payload)
    
    def _uploadfiletofilesystem(FSYSuploadDetails):
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
        upload_url = "%s%s" % (uploadUrl, FSYSuploadDetails['upload_path'])
        FSYSparams = {'qqfile': uploadFilepath,
                      'import_record': uploadDatasetID,
                      'source_type': uploadDatatype   }
        return requests.post(upload_url,
                             params=FSYSparams,
                             files={'filename': open(uploadFilepath, 'rb')},
                             headers=uploadHeader)
    
    # Get the upload details.
    upload_details = requests.get(uploadUrl+'/data/get_upload_details/', headers=uploadHeader)
    upload_details = upload_details.json()

    filename = os.path.basename(uploadFilepath)

    if upload_details['upload_mode'] == 'S3':
        return _uploadfiletoAWS(upload_details)
    elif upload_details['upload_mode'] == 'filesystem':
        return _uploadfiletofilesystem(upload_details)
    else:
        raise RuntimeError("Upload mode unknown: %s" %
                           upload_details['upload_mode'])
                             
def checkStatus(resultOut, fileOut, PIIDflag=None): 
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    if resultOut.status_code in [200, 403, 401]:
        if 'status' in resultOut.json().keys() and resultOut.json()['status'] == 'error':
            print ('...not passed')
            msg = resultOut.json()['message']
            pprint.pprint(msg, stream=fileOut)
            fileOut.close()
            raise RuntimeError(msg)
        elif 'success' in resultOut.json().keys() and resultOut.json()['success'] == False:
            print ('...not passed')
            msg = resultOut.json()
            pprint.pprint(msg, stream=fileOut)
            fileOut.close()
            raise RuntimeError(msg)
            fileOut.close
        else:
            if PIIDflag == 'organizations': 
                print ('...passed')
                pprint.pprint('Number of organizations:    '+
                              str(len(resultOut.json()['organizations'][0])), 
                              stream=fileOut)
            elif PIIDflag == 'users':    
                print ('...passed')
                pprint.pprint('Number of users:    '+
                              str(len(resultOut.json()['users'][0])), 
                              stream=fileOut)
            else:
                print ('...passed')
                pprint.pprint(resultOut.json(), stream=fileOut)
    else:
        print ('...not passed')
        msg = resultOut.reason
        pprint.pprint(msg, stream=fileOut) 
        fileOut.close()
        raise RuntimeError(msg)
        fileOut.close
    return 
                       
#---
# Set up the request credentials 
hostname = raw_input('Hostname: \t')
mainURL = raw_input('Host URL: \t')
Username = raw_input('Username: \t')
APIKEY = raw_input('APIKEY: \t')
Header = {'authorization':':'.join([Username.lower(),APIKEY])}
#NOTE: The header only accepts lower case usernames. 

# Set up output file
fileout = open(hostname+'_seedhost.txt', 'w')  
fileout.write ('Hostname: \t'+hostname)
fileout.write ('\nURL: \t\t'+mainURL)
fileout.write ('\nTest Date:\t'+dt.datetime.strftime(dt.datetime.now(), 
                                                     '%Y-%m-%d %H:%M:%S'))
#-- Accounts
print ('\n-------Accounts-------\n')
fileout.write ('\n-------Accounts-------\n')
# Retrieve the user profile 
print ('API Function: get_user_profile'),
fileout.write ('API Function: get_user_profile\n')
result = requests.get(mainURL+'/app/accounts/get_user_profile',
                      headers=Header)
checkStatus(result, fileout)

# Retrieve the organizations 
print ('API Function: get_organizations'),
fileout.write ('API Function: get_organizations\n')
result = requests.get(mainURL+'/app/accounts/get_organizations/',
                      headers=Header)
# TODO Return number of organizations 
checkStatus(result, fileout, PIIDflag='organizations')
    
# # Get the organization id to be used.
# # NOTE: Loop through the organizations and get the org_id 
# # where the organization owner is 'Username' else get the first organization. 
orgs_result= result.json()
for ctr in range(len(orgs_result['organizations'])):
    if orgs_result['organizations'][ctr]['owners'][0]['email'] == Username:
        organizationID = orgs_result['organizations'][ctr]['org_id']
        break
    else: 
        organizationID = orgs_result['organizations'][0]['org_id']
    
# Get the organization details 
print ('API Function: get_organization'),
fileout.write ('API Function: get_organization\n')
modURL = mainURL+'/app/accounts/get_organization/?organization_id='+str(organizationID)
result = requests.get(modURL,
                      headers=Header)
checkStatus(result, fileout)
    
# Change user profile 
# NOTE: Make sure these credentials are ok.
print ('API Function: update_user'),
fileout.write ('API Function: update_user\n')
user_payload={'user': {'first_name': 'C', 
                       'last_name':'Custodio',
                       'email': Username}} 
result = requests.post(mainURL+'/app/accounts/update_user/',
                      headers=Header,
                      data=json.dumps(user_payload))
checkStatus(result, fileout)
                                            
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
# checkStatus(result, fileout)

# Get organization users
print ('API Function: get_organizations_users'),
fileout.write ('API Function: get_organizations_users\n')
org_payload = {'organization_id': organizationID}
result = requests.post(mainURL+'/app/accounts/get_organizations_users/',
                      headers=Header,
                      data=json.dumps(org_payload))
checkStatus(result, fileout, PIIDflag='users')

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
# checkStatus(result, fileout)

# Get organizations settings
print ('API Function: get_query_threshold'),
fileout.write ('API Function: get_query_threshold\n')
result = requests.get(mainURL+'/app/accounts/get_query_threshold/',
                      headers=Header,
                      params={'organization_id':organizationID})
checkStatus(result, fileout)

print ('API Function: get_shared_fields'),
fileout.write ('API Function: get_shared_fields\n')
result = requests.get(mainURL+'/app/accounts/get_shared_fields/',
                      headers=Header,
                      params={'organization_id':organizationID})
checkStatus(result, fileout)

#-- Dataset 
print ('\n-------Dataset-------\n')
fileout.write ('\n-------Dataset-------\n')
# Set up directory for file uploads
sample_dir = "data"

# Load raw files. 
raw_building_file = os.path.relpath(os.path.join(sample_dir, 'covered-buildings-sample.csv'))
assert (os.path.isfile(raw_building_file)), 'Missing file '+raw_building_file 

pm_building_file = os.path.relpath(os.path.join(sample_dir, 'portfolio-manager-sample.csv'))
assert (os.path.isfile(pm_building_file)), "Missing file "+pm_building_file 

# Create a dataset 
print ('API Function: create_dataset'),
fileout.write ('API Function: create_dataset\n')
payload={'organization_id': organizationID,
         'name': 'API Test'}
result = requests.post(mainURL+'/app/create_dataset/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

# Get the dataset id to be used 
datasetID = result.json()['id']

print ('\n|---Covered Building File---|\n')
fileout.write ('\n|---Covered Building File---|\n')
# Upload the covered-buildings-sample file 
print ('API Function: upload_file'),
fileout.write ('API Function: upload_file\n')
result = uploadfile(Header, 
                         raw_building_file, 
                         mainURL, 
                         datasetID, 
                         'Assessed Raw')
checkStatus(result, fileout)

# Get import ID 
importID = result.json()['import_file_id']

# Save the data to BuildingSnapshots
print ('API Function: save_raw_data'),
fileout.write ('API Function: save_raw_data\n')
payload = {'file_id':importID,
           'organization_id': organizationID}
result = requests.post(mainURL+'/app/save_raw_data/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)

# Save the column mappings. 
print ('API Function: save_column_mappings'),
fileout.write ('API Function: save_column_mappings\n') 
payload = {'import_file_id': importID,
           'organization_id': organizationID}
payload['mappings'] = [[u'city',u'City'],
                       [u'postal_code',u'Zip'],
                       [u'gross_floor_area',u'GBA'],
                       [u'building_count',u'BLDGS'],
                       [u'tax_lot_id',u'UBI'],
                       [u'state_province',u'State'],
                       [u'address_line_1',u'Address'],
                       [u'owner',u'Owner'],
                       [u'use_description',u'Property Type'],
                       [u'year_built',u'AYB_YearBuilt']]
result = requests.get(mainURL+'/app/save_column_mappings/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

# Map the buildings with new column mappings.
print ('API Function: remap_buildings'),
fileout.write ('API Function: remap_buildings\n')  
payload = {'file_id': importID,
           'organization_id': organizationID}
result = requests.get(mainURL+'/app/remap_buildings/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)
                      
# Get the mapping suggestions
print ('API Function: get_column_mapping_suggestions'),
fileout.write ('API Function: get_column_mapping_suggestions\n')
payload = {'import_file_id': importID,
           'org_id': organizationID}
result = requests.get(mainURL+'/app/get_column_mapping_suggestions/',
                      headers=Header,
                      data=json.dumps(payload))
if result.status_code == 200: 
    print('...passed')
    pprint.pprint(result.json()['suggested_column_mappings'], stream=fileout)
else: 
    print('...not passed')
    pprint.pprint(result.reason, stream=fileout)

# Match uploaded buildings with buildings already in the organization.
print ('API Function: start_system_matching'),
fileout.write ('API Function: start_system_matching\n') 
payload = {'file_id': importID,
           'organization_id': organizationID}
result = requests.post(mainURL+'/app/start_system_matching/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)

print ('\n|---Portfolio Manager File---|\n')
fileout.write ('\n|---Portfolio Manager File---|\n')
# Upload the portfolio-manager-sample file.
print ('API Function: upload_file'),
fileout.write ('API Function: upload_file\n')
result = uploadfile(Header, 
                         pm_building_file, 
                         mainURL, 
                         datasetID, 
                         'Portfolio Raw')
checkStatus(result, fileout)

# Get import ID 
importID = result.json()['import_file_id']

# Save the data to BuildingSnapshots
print ('API Function: save_raw_data'),
fileout.write ('API Function: save_raw_data\n')
payload = {'file_id':importID,
           'organization_id': organizationID}
result = requests.post(mainURL+'/app/save_raw_data/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)
    
# Save the column mappings. 
print ('API Function: save_column_mappings'),
fileout.write ('API Function: save_column_mappings\n') 
payload = {'import_file_id': importID,
           'organization_id': organizationID}
payload['mappings'] = [[u'city',u'City'],
                        [u'energy_score',u'ENERGY STAR Score'],
                        [u'state_province',u'State/Province'],
                        [u'site_eui',u'Site EUI (kBtu/ft2)'],
                        [u'year_ending',u'Year Ending'],
                        [u'source_eui_weather_normalized','Weather Normalized Source EUI (kBtu/ft2)'],
                        [u'Parking - Gross Floor Area',u'Parking - Gross Floor Area (ft2)'],
                        [u'address_line_1',u'Address 1'],
                        [u'Portfolio Manager Property ID',u'Property Id'],
                        [u'address_line_2',u'Address 2'],
                        [u'source_eui',u'Source EUI (kBtu/ft2)'],
                        [u'release_date',u'Release Date'],
                        [u'National Median Source EUI',u'National Median Source EUI (kBtu/ft2)'],
                        [u'site_eui_weather_normalized',u'Weather Normalized Site EUI (kBtu/ft2)'],
                        [u'National Median Site EUI',u'National Median Site EUI (kBtu/ft2)'],
                        [u'year_built',u'Year Built'],
                        [u'postal_code',u'Postal Code'],
                        [u'owner',u'Organization'],
                        [u'property_name',u'Property Name'],
                        [u'Property Floor Area (Buildings and Parking)',u'Property Floor Area (Buildings and Parking) (ft2)'],
                        [u'Total GHG Emissions',u'Total GHG Emissions (MtCO2e)'],
                        [u'generation_date',u'Generation Date']]
result = requests.get(mainURL+'/app/save_column_mappings/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

# Map the buildings with new column mappings.
print ('API Function: remap_buildings'),
fileout.write ('API Function: remap_buildings\n')  
payload = {'file_id': importID,
           'organization_id': organizationID}
result = requests.get(mainURL+'/app/remap_buildings/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)
                      
# Get the mapping suggestions
print ('API Function: get_column_mapping_suggestions'),
fileout.write ('API Function: get_column_mapping_suggestions\n')
payload = {'import_file_id': importID,
           'org_id': organizationID}
result = requests.get(mainURL+'/app/get_column_mapping_suggestions/',
                      headers=Header,
                      data=json.dumps(payload))
if result.status_code == 200: 
    print('...passed')
    pprint.pprint(result.json()['suggested_column_mappings'], stream=fileout)
else: 
    print('...not passed')
    pprint.pprint(result.reason, stream=fileout)

# Match uploaded buildings with buildings already in the organization.
print ('API Function: start_system_matching'),
fileout.write ('API Function: start_system_matching\n') 
payload = {'file_id': importID,
           'organization_id': organizationID}
result = requests.post(mainURL+'/app/start_system_matching/',
                      headers=Header,
                      data=json.dumps(payload))
checkStatus(result, fileout)

time.sleep(10)
progress = requests.get(mainURL+'/app/progress/',
                        headers=Header,
                        data=json.dumps({'progress_key':result.json()['progress_key']}))
pprint.pprint (progress.json(), stream=fileout)

print ('\n'),
fileout.write ('\n')
# Check number of matched and unmatched BuildingSnapshots
print ('API Function: get_PM_filter_by_counts'),
fileout.write ('API Function: get_PM_filter_by_counts\n')
result = requests.get(mainURL+'/app/get_PM_filter_by_counts/',
                      headers=Header,
                      params={'import_file_id':importID})
checkStatus(result, fileout)     

# Search CanonicalBuildings
print ('API Function: search_buildings'),
fileout.write ('API Function: search_buildings\n') 
search_payload = {'filter_params':{u'address_line_1': u'94734 SE Honeylocust Street' }}
result = requests.get(mainURL+'/app/search_buildings/',
                      headers=Header,
                      data=json.dumps(search_payload))
checkStatus(result, fileout)     


#-- Project 
print ('\n-------Project-------\n')
fileout.write ('\n-------Project-------\n')
# Create a Project for 'Condo' in 'use_description'
print ('API Function: create_project'),
fileout.write ('API Function: create_project\n')
newproject_payload = {'project': {'name': 'New Project', 
                                'compliance_type': 'describe compliance type', 
                                'description': 'project description'},
                      'organization_id': organizationID}
result = requests.post(mainURL+'/app/projects/create_project/',
                       headers=Header,
                       data=json.dumps(newproject_payload))
checkStatus(result, fileout)     

# Get project slug 
projectSlug = result.json()['project_slug']

# Get the projects for the organization
print ('API Function: get_project'),
fileout.write ('API Function: get_project\n')
result = requests.get(mainURL+'/app/projects/get_projects/',
                       headers=Header,
                       params={'organization_id':organizationID})
checkStatus(result, fileout)  

# Populate project by search buildings result 
print ('API Function: add_buildings_to_project'),
fileout.write ('API Function: add_buildings_to_project\n')
projectbldg_payload = {'project':{'status':'active',
                                  'project_slug':projectSlug,
                                  'slug':projectSlug, 
                                  'select_all_checkbox':True, 
                                  'selected_buildings':[],
                                  'filter_params':{'use_description':'CONDO'}}, 
                       'organization_id':organizationID}
result = requests.post(mainURL+'/app/projects/add_buildings_to_project/',
                       headers=Header,
                       data=json.dumps(projectbldg_payload))
checkStatus(result, fileout)  

# Get the percent/progress of buildings added to project 
time.sleep(10)
progress = requests.post(mainURL+'/app/projects/get_adding_buildings_to_project_status_percentage/',
                        headers=Header,
                        data=json.dumps({'project_loading_cache_key':result.json()['project_loading_cache_key']}))
pprint.pprint (progress.json(), stream=fileout)

#-- Labels 
print ('\n-------Labels-------\n')
fileout.write ('\n-------Labels-------\n')
# Create label
print ('API Function: add_label (test label) '),
fileout.write ('API Function: add_label\n')
label_payload = {'label': {'name': 'test label', 
                           'color': 'gray'} }
result = requests.post(mainURL+'/app/projects/add_label/',
                        headers=Header,
                        data=json.dumps(label_payload))
checkStatus(result, fileout)  

# Get labelID
labelID = result.json()['label_id']

# Get organization labels                
print ('API Function: get_labels'),
fileout.write ('API Function: get_labels\n')
result = requests.get(mainURL+'/app/projects/get_labels/',
                        headers=Header)
checkStatus(result, fileout)  

# Apply to buildings that have ENERGY STAR Score > 50
print ('API Function: apply_label'),
fileout.write ('API Function: apply_label\n')
payload = {'label':{'id':labelID},
                    'project_slug':projectSlug,
                    'buildings':[],
                    'select_all_checkbox':True,
                    'search_params':{'filter_params':{'project__slug':projectSlug}} }
result = requests.post(mainURL+'/app/projects/apply_label/',
                        headers=Header,
                        data=json.dumps(payload))
checkStatus(result, fileout)  

#-- Export  
print ('\n-------Export-------\n')
fileout.write ('\n-------Export-------\n')
# Export all buildings.
print ('API Function: export_buildings'),
fileout.write ('API Function: export_buildings\n')
export_payload = {'export_name': 'project_buildings', 
                  'export_type': "csv",
                  'select_all_checkbox': True,
                  'filter_params':{'project__slug':projectSlug}}
result = requests.post(mainURL+'/app/export_buildings/',
                        headers=Header,
                        data=json.dumps(export_payload))
checkStatus(result, fileout)  

# Get exportID
exportID = result.json()['export_id']

time.sleep(15)
progress = requests.post(mainURL+'/app/export_buildings/progress/',
                        headers=Header,
                        data=json.dumps({'export_id':exportID}))
pprint.pprint (progress.json(), stream=fileout)
time.sleep(15)

print ('API Function: export_buildings_download'),
fileout.write ('API Function: export_buildings_download\n')
result = requests.post(mainURL+'/app/export_buildings/download/',
                        headers=Header,
                        data=json.dumps({'export_id':exportID}))
checkStatus(result, fileout)  

fileout.close()
