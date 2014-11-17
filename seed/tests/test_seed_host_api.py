"""API Testing for SEED Hosts."""

import os
import requests
import pprint
import json
import numpy as np
import datetime as dt
import time
from calendar import timegm


# Three-step upload process 
def uploadfiletoAWS(AWSheader, AWSfilepath, AWSurl, AWSdatasetID, AWSdatatype):
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
        - filepath: full path to file
        - upload_details: Results from 'get_upload_details' endpoint;
            contains details about where to send file and how.
        - import_record_id: What ImportRecord to associate file with.
        - source_type: Type of data in file (Assessed Raw, Portfolio Raw)

        Returns:
            {"import_file_id": 54,
             "success": true,
             "filename": "DataforSEED_dos15.csv"}
     """
    # Get the upload details.
    upload_details = requests.get(AWSurl+'/data/get_upload_details/', headers=AWSheader)
    upload_details = upload_details.json()
    
    filename = os.path.basename(AWSfilepath)
    #Step 1: get the request signed
    sig_uri = upload_details['signature']

    now = dt.datetime.utcnow()
    expires = now + dt.timedelta(hours=1)
    now_ts = timegm(now.timetuple())
    key = 'data_imports/%s.%s' % (filename, now_ts)

    payload = {}
    payload['expiration'] = expires.isoformat() + 'Z'
    payload['conditions'] = [
        {'bucket': upload_details['aws_bucket_name']},
        {'Content-Type': 'text/csv'},
        {'acl': 'private'},
        {'success_action_status': '200'},
        {'key': key}
    ]

    sig_result = requests.post(AWSurl+sig_uri, 
                              headers=AWSheader,
                              data=json.dumps(payload))
    if sig_result.status_code != 200:
        msg = "Something went wrong with signing document."
        raise RuntimeError(msg)
    else: 
        sig_result = sig_result.json()

    #Step 2: upload the file to S3
    upload_url = "http://%s.s3.amazonaws.com/" % (upload_details['aws_bucket_name'])

    #s3 expects multipart form encoding with files at the end, so this
    #payload needs to be a list of tuples; the requests library will encode
    #it property if sent as the 'files' parameter.
    s3_payload = [
        ('key', key),
        ('AWSAccessKeyId', upload_details['aws_client_key']),
        ('Content-Type', 'text/csv'),
        ('success_action_status', '200'),
        ('acl', 'private'),
        ('policy', sig_result['policy']),
        ('signature', sig_result['signature']),
        ('file', (filename,open(AWSfilepath, 'rb')))
    ]

    result = requests.post(upload_url, 
                           files=s3_payload)

    if result.status_code != 200:
        msg = "Something went wrong with the S3 upload: %s " % result.reason
        raise RuntimeError(msg)
        

    #Step 3: Notify SEED about the upload
    completion_uri = upload_details['upload_complete']
    completion_payload = {
        'import_record': AWSdatasetID,
        'key': key,
        'source_type': AWSdatatype
    }
    return requests.get(AWSurl+completion_uri,
                       headers=AWSheader,
                       params=completion_payload)

def checkStatus(resultOut, fileOut): 
    """Checks the status of the API endpoint and makes the appropriate print outs."""
    if resultOut.status_code == 200:
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
        else:
            print ('...passed')
            pprint.pprint(resultOut.json(), stream=fileOut)
    else:
        print ('...not passed')
        msg = resultOut.reason
        pprint.pprint(msg, stream=fileOut) 
        fileOut.close()
        raise RuntimeError(msg)
    return 
                       
#---
# Set up the request credentials 
hostname = raw_input('Hostname: \t')
mainURL = raw_input('Host URL: \t')
Username = raw_input('Username: \t')
APIKEY = raw_input('APIKEY: \t')
Header = {'authorization':':'.join([Username,APIKEY])}

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

# ? Create user API key

# Retrieve the organizations 
print ('API Function: get_organizations'),
fileout.write ('API Function: get_organizations\n')
result = requests.get(mainURL+'/app/accounts/get_organizations/',
                      headers=Header)
checkStatus(result, fileout)
    
# Get the organization id to be used.
# NOTE: Loop through the organizations and get the org_id 
# where the organization owner is 'Username'
orgs_result= result.json()
for ctr in range(len(orgs_result['organizations'])):
    if orgs_result['organizations'][ctr]['owners'][0]['email'] == Username:
        organizationID = orgs_result['organizations'][ctr]['org_id']
        break
    
# Get the organization details 
print ('API Function: get_organization'),
fileout.write ('API Function: get_organization\n')
modURL = mainURL+'/app/accounts/get_organization/?organization_id='+str(organizationID)
result = requests.get(modURL,
                      headers=Header)
checkStatus(result, fileout)
    
# Change user profile 
print ('API Function: update_user'),
fileout.write ('API Function: update_user\n')
user_payload={'user': {'first_name': 'C', 
                       'last_name':'Custodio',
                       'email': 'cycustodio@lbl.gov'}} 
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
                    # 'role': {'name':'Owner',
                             # 'value': 'owner'}, 
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
checkStatus(result, fileout)

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
sample_dir = "seed\\tests\\data"

# Load raw files. 
raw_building_file = os.path.relpath(os.path.join(sample_dir, 'covered-buildings-sample.csv'))
assert (os.path.isfile(raw_building_file)), 'Missing file '+raw_building_file 

pm_building_file = os.path.relpath(os.path.join(sample_dir, 'portfolio-manager-sample.csv'))
assert (os.path.isfile(pm_building_file)), "Missing file "+raw_building_file 

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

# Upload the combined_buildings file 
print ('API Function: upload_file'),
fileout.write ('API Function: upload_file\n')
result = uploadfiletoAWS(Header, 
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
payload = {'file_id':importID}
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
payload['mappings'] = [[u'City', u'city'],
                       [u'Zip',u'postal_code'],
                       [u'GBA',u'gross_floor_area'],
                       [u'BLDGS',u'building_count'],
                       [u'UBI',u'tax_lot_id'],
                       [u'State',u'state_province'],
                       [u'Address',u'address_line_1'],
                       [u'Owner',u'owner'],
                       [u'Property Type',u'use_description'],
                       [u'AYB_YearBuilt',u'year_built']]
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
# Create a Project for CONDO in use_description
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
                                  'filter_params':{'use_description':'CONDO'}} 
                      }
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
export_payload = {'export_name': 'all_bldgs', 
                  'export_type': "csv",
                  'select_all_checkbox': True }
result = requests.post(mainURL+'/app/export_buildings/',
                        headers=Header,
                        data=json.dumps(export_payload))
checkStatus(result, fileout)  

# Get exportID
exportID = result.json()['export_id']

time.sleep(10)
progress = requests.post(mainURL+'/app/export_buildings/progress/',
                        headers=Header,
                        data=json.dumps({'export_id':exportID}))
pprint.pprint (progress.json(), stream=fileout)


print ('API Function: export_buildings_download'),
fileout.write ('API Function: export_buildings_download\n')
result = requests.post(mainURL+'/app/export_buildings/download/',
                        headers=Header,
                        data=json.dumps({'export_id':exportID}))
checkStatus(result, fileout)  

fileout.close()
