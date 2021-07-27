# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime as dt
import json
import pprint
import time
import uuid
from builtins import str

import requests
from seed_readingtools import (
    check_status,
    check_progress,
    read_map_file,
    upload_file,
    write_out_django_debug
)


def upload_match_sort(header, main_url, organization_id, dataset_id, cycle_id, filepath, filetype,
                      mappingfilepath, log):
    # Upload the covered-buildings-sample file
    print('API Function: upload_file\n'),
    partmsg = 'upload_file'
    result = upload_file(header, organization_id, filepath, main_url, dataset_id, filetype)
    check_status(result, partmsg, log)

    # Get import ID
    import_id = result.json()['import_file_id']

    # Save the data
    print('API Function: save_raw_data\n'),
    partmsg = 'save_raw_data'
    payload = {
        'cycle_id': cycle_id
    }
    result = requests.post(
        main_url + '/api/v3/import_files/{}/start_save_data/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header,
        json=payload
    )
    check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Get the mapping suggestions
    print('API Function: get_column_mapping_suggestions\n'),
    partmsg = 'get_column_mapping_suggestions'
    result = requests.get(
        main_url + '/api/v3/import_files/{}/mapping_suggestions/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header)
    check_status(result, partmsg, log, piid_flag='mappings')

    # Save the column mappings
    print('API Function: save_column_mappings\n'),
    partmsg = 'save_column_mappings'
    payload = {'mappings': read_map_file(mappingfilepath)}
    result = requests.post(
        main_url + '/api/v3/organizations/{}/column_mappings/'.format(organization_id),
        params={"import_file_id": import_id},
        headers=header,
        json=payload
    )
    check_status(result, partmsg, log)

    # Perform mapping
    print('API Function: perform_mapping\n'),
    partmsg = 'save_column_mappings'
    result = requests.post(
        main_url + '/api/v3/import_files/{}/map/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header
    )
    print(result.json())
    check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Get Data Quality Message
    print('API Function: data_quality\n'),
    partmsg = 'data_quality'

    result = requests.post(
        main_url + '/api/v3/import_files/{}/start_data_quality_checks/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header
    )
    print(result.json())
    check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    result = requests.get(
        main_url + '/api/v3/data_quality_checks/results/',
        headers=header,
        params={"organization_id": organization_id, "run_id": import_id}
    )
    check_status(result, partmsg, log, piid_flag='data_quality')

    # Match uploaded buildings with buildings already in the organization.
    print('API Function: start_system_matching_and_geocoding\n'),
    partmsg = 'start_system_matching_and_geocoding'
    payload = {'file_id': import_id, 'organization_id': organization_id}

    result = requests.post(
        main_url + '/api/v3/import_files/{}/start_system_matching_and_geocoding/'.format(import_id),
        headers=header,
        params={"organization_id": organization_id},
        json=payload
    )
    result = check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Check number of matched and unmatched records
    print('API Function: matching_and_geocoding_results\n'),
    partmsg = 'matching_and_geocoding_results'

    result = requests.get(
        main_url + '/api/v3/import_files/{}/matching_and_geocoding_results/'.format(import_id),
        headers=header,
        params={"organization_id": organization_id})
    check_status(result, partmsg, log)


def search_and_project(header, main_url, organization_id, log):
    # Search CanonicalBuildings
    print('API Function: search_buildings\n'),
    partmsg = 'search_buildings'
    search_payload = {'filter_params': {'address_line_1': '94734 SE Honeylocust Street'}}

    result = requests.get(main_url + '/api/v1/search_buildings/',
                          headers=header,
                          data=json.dumps(search_payload))
    check_status(result, partmsg, log)

    # Project
    print('\n-------Project-------\n')

    # Create a Project for 'Condo' in 'use_description'
    print('API Function: create_project\n'),
    partmsg = 'create_project'
    time1 = dt.datetime.now()
    newproject_payload = {
        'name': 'New Project_' + str(time1.day) + str(time1.second),
        'compliance_type': 'describe compliance type',
        'description': 'project description'
    }
    result = requests.post(
        main_url + '/api/v2/projects/',
        headers=header,
        params=json.dumps({'organization_id': organization_id}),
        data=json.dumps(newproject_payload)
    )
    write_out_django_debug(partmsg, result)
    check_status(result, partmsg, log)

    # Get project slug
    project_slug = result.json()['project_slug']

    # Get the projects for the organization
    print('API Function: get_project\n'),
    partmsg = 'get_project'

    result = requests.get(main_url + '/api/v2/projects/',
                          headers=header,
                          params=json.dumps(
                              {'project_slug': project_slug, 'organization_id': organization_id}))
    check_status(result, partmsg, log)

    # Populate project by search buildings result
    print('API Function: add_buildings_to_project\n'),
    partmsg = 'add_buildings_to_project'
    projectbldg_payload = {'project': {'status': 'active',
                                       'project_slug': project_slug,
                                       'slug': project_slug,
                                       'select_all_checkbox': True,
                                       'selected_buildings': [],
                                       'filter_params': {'use_description': 'CONDO'}},
                           'organization_id': organization_id}

    result = requests.post(main_url + '/app/projects/add_buildings_to_project/',
                           headers=header,
                           data=json.dumps(projectbldg_payload))
    time.sleep(10)
    check_status(result, partmsg, log)

    # Get the percent/progress of buildings added to project
    progress = requests.post(
        main_url + '/app/projects/get_adding_buildings_to_project_status_percentage/',
        headers=header,
        data=json.dumps({'project_loading_cache_key': result.json()['project_loading_cache_key']}))
    log.debug(pprint.pformat(progress.json()))


def account(header, main_url, username, log):
    # Retrieve the user id key for later retrievals
    print('API Function: current_user_id\n')
    result = requests.get(
        main_url + '/api/v3/users/current/',
        headers=header
    )
    user_pk = json.loads(result.content)['pk']

    # Retrieve the user profile
    print('API Function: get_user_profile\n')
    partmsg = 'get_user_profile'
    result = requests.get(main_url + '/api/v3/users/%s/' % user_pk,
                          headers=header)
    check_status(result, partmsg, log)

    # Retrieve the organizations
    print('API Function: get_organizations\n'),
    partmsg = 'get_organizations'
    result = requests.get(main_url + '/api/v3/organizations/',
                          headers=header)
    check_status(result, partmsg, log, piid_flag='organizations')

    # Get the organization id to be used.
    # NOTE: Loop through the organizations and get the org_id
    # where the organization owner is 'username' else get the first organization.
    orgs_result = result.json()

    for org in orgs_result['organizations']:
        try:
            if org['owners'][0]['email'] == username:
                organization_id = org['org_id']
                break
        except IndexError:
            pass
    else:
        organization_id = orgs_result['organizations'][0]['org_id']

    # Get the organization details
    partmsg = 'get_organization (2)'
    mod_url = main_url + '/api/v3/organizations/%s' % str(organization_id)
    result = requests.get(mod_url, headers=header)
    check_status(result, partmsg, log)

    # Change user profile
    # NOTE: Make sure these credentials are ok.
    print('API Function: update_user\n'),
    partmsg = 'update_user'
    user_payload = {
        'first_name': 'Sherlock',
        'last_name': 'Holmes',
        'email': username
    }
    result = requests.put(main_url + '/api/v3/users/%s/' % user_pk,
                          headers=header,
                          data=user_payload)
    check_status(result, partmsg, log)

    # Get organization users
    print('API Function: get_organizations_users\n'),
    partmsg = 'get_organizations_users'
    result = requests.get(main_url + '/api/v3/organizations/%s/users/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log, piid_flag='users')

    # Get organizations settings
    print('API Function: get_query_treshold\n'),
    partmsg = 'get_query_threshold'
    result = requests.get(main_url + '/api/v3/organizations/%s/query_threshold/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log)

    # Get shared fields
    print('API Function: get_shared_fields\n'),
    partmsg = 'get_shared_fields'
    result = requests.get(main_url + '/api/v3/organizations/%s/shared_fields/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log)

    # Create an organization
    print('API Function: create_org\n'),
    partmsg = 'create_org'
    org_name = 'TestOrg_{}'.format(str(uuid.uuid4()))
    payload = {
        'user_id': user_pk,
        'organization_name': org_name  # hopefully ensuring a unique org name
    }
    result = requests.post(main_url + '/api/v3/organizations/',
                           headers=header,
                           json=payload)
    check_status(result, partmsg, log)
    org_id = result.json()['organization']['org_id']

    # Delete an organization
    print('API Function: delete_org\n'),
    partmsg = 'delete_org'
    result = requests.delete(main_url + '/api/v3/organizations/%s/' % org_id,
                             headers=header)
    check_status(result, partmsg, log)

    # Create a suborganization
    print('API Function: create_sub_org\n'),
    partmsg = 'create_sub_org'
    payload = {
        'sub_org_name': 'TestSuborg',
        'sub_org_owner_email': username
    }
    result = requests.post(main_url + '/api/v3/organizations/%s/sub_org/' % organization_id,
                           headers=header,
                           data=payload)
    check_status(result, partmsg, log)
    suborg_id = result.json()['organization_id']

    # Delete a suborganization
    print('API Function: delete_sub_org\n'),
    partmsg = 'delete_sub_org'
    result = requests.delete(main_url + '/api/v3/organizations/%s/' % suborg_id,
                             headers=header)
    check_status(result, partmsg, log)

    return organization_id


def delete_set(header, main_url, organization_id, dataset_id, log):
    # Delete all buildings
    # print('API Function: delete_inventory\n'),
    # partmsg = 'delete_buildings'
    # result = requests.delete(
    #     main_url + '/app/delete_organization_inventory/',
    #     headers=header,
    #     params={'organization_id': organization_id}
    # )
    # check_status(result, partmsg, log)

    # Delete dataset
    print('API Function: delete_dataset\n'),
    partmsg = 'delete_dataset'
    result = requests.delete(
        main_url + '/api/v3/datasets/{}/'.format(dataset_id),
        headers=header,
        params={'organization_id': organization_id},
    )
    check_status(result, partmsg, log)

    # Delete project
    # print('API Function: delete_project\n'),
    # partmsg = 'delete_project'
    # payload = {'organization_id': organization_id,
    #            'project_slug': project_slug}
    #
    # result = requests.delete(main_url + '/app/projects/delete_project/',
    #                          headers=header,
    #                          data=json.dumps(payload))
    # check_status(result, partmsg, log)


def cycles(header, main_url, organization_id, log):
    print('API Function: get_cycles\n')
    partmsg = 'get_cycles'
    result = requests.get(main_url + '/api/v3/cycles/',
                          headers=header,
                          params={'organization_id': organization_id})
    check_status(result, partmsg, log, piid_flag='cycles')

    cycles = result.json()['cycles']
    print("current cycles are {}".format(cycles))
    for cyc in cycles:
        if cyc['name'] == 'TestCycle':
            cycle_id = cyc['id']
            break
    else:
        # Create cycle (only if it does not exist, until there is a function to delete cycles)
        print('API Function: create_cycle\n')
        partmsg = 'create_cycle'
        payload = {
            'start': "2015-01-01T08:00",
            'end': "2016-01-01T08:00",
            'name': "TestCycle"
        }
        result = requests.post(main_url + '/api/v3/cycles/',
                               headers=header,
                               params={'organization_id': organization_id},
                               json=payload)
        check_status(result, partmsg, log)

        cycle_id = result.json()['cycles']['id']

    # Update cycle
    print('\nAPI Function: update_cycle')
    partmsg = 'update_cycle'
    payload = {
        'start': "2015-01-01T08:00",
        'end': "2016-01-01T08:00",
        'name': "TestCycle",
        'id': cycle_id
    }
    result = requests.put(main_url + '/api/v3/cycles/{}/'.format(cycle_id),
                          headers=header,
                          params={'organization_id': organization_id},
                          json=payload)
    check_status(result, partmsg, log)

    # TODO: Test deleting a cycle
    return cycle_id


def labels(header, main_url, organization_id, cycle_id, log):

    # Create label
    print('API Function: create_label\n')
    partmsg = 'create_label'
    params = {
        'organization_id': organization_id
    }
    payload = {
        'name': 'TestLabel',
        'color': 'red'
    }
    result = requests.post(main_url + '/api/v3/labels/',
                           headers=header,
                           params=params,
                           json=payload)
    check_status(result, partmsg, log)
    label_id = result.json()['id']

    # Get IDs for all properties
    params = {
        'organization_id': organization_id,
        'cycle': cycle_id,
        'page': 1,
        'per_page': 999999999
    }
    result = requests.post(main_url + '/api/v3/properties/filter/',
                           headers=header,
                           params=params)
    inventory_ids = [prop['property_view_id'] for prop in result.json()['results']]

    # Apply label to properties
    print('API Function: apply_label\n')
    partmsg = 'apply_label'
    params = {
        'organization_id': organization_id
    }
    payload = {
        'add_label_ids': [label_id],
        'inventory_ids': inventory_ids
    }
    result = requests.put(main_url + '/api/v3/labels_property/',
                          headers=header,
                          params=params,
                          json=payload)
    check_status(result, partmsg, log)

    # Delete label
    print('API Function: delete_label\n')
    partmsg = 'delete_label'
    params = {
        'organization_id': organization_id
    }
    result = requests.delete(main_url + '/api/v3/labels/%s/' % label_id,
                             headers=header,
                             params=params)
    check_status(result, partmsg, log)


def data_quality(header, main_url, organization_id, log):

    # get the data quality rules for the organization
    print('API Function: get_data_quality_rules\n')
    partmsg = 'get_data_quality_rules'
    result = requests.get(
        main_url + f'/api/v3/data_quality_checks/{organization_id}/rules/',
        headers=header
    )
    check_status(result, partmsg, log)

    # create a new rule
    print('API Function: create_data_quality_rule\n')
    partmsg = 'create_data_quality_rule'
    payload = {
        'field': 'city',
        'enabled': True,
        'data_type': 1,
        'condition': 'not_null',
        'rule_type': 1,
        'required': False,
        'not_null': False,
        'min': None,
        'max': None,
        'text_match': None,
        'severity': 1,
        'units': '',
        'status_label': None,
        'table_name': "PropertyState"
    }
    result = requests.post(
        main_url + f'/api/v3/data_quality_checks/{organization_id}/rules/',
        headers=header,
        json=payload
    )
    new_rule_id = result.json().get('id')
    check_status(result, partmsg, log)

    # delete the new rule
    print('API Function: delete_data_quality_rule\n')
    partmsg = 'delete_data_quality_rule'
    result = requests.delete(
        main_url + f'/api/v3/data_quality_checks/{organization_id}/rules/{new_rule_id}/',
        headers=header
    )
    check_status(result, partmsg, log)

    # get some property view ids
    result = requests.get(
        main_url + '/api/v3/property_views/',
        headers=header
    )
    prop_view_ids = [prop['id'] for prop in result.json()['property_views']]

    # create a new data quality check process
    print('API Function: create_data_quality_check\n')
    partmsg = 'create_data_quality_check'
    payload = {
        'property_view_ids': prop_view_ids,
        'taxlot_view_ids': []
    }
    result = requests.post(
        main_url + f'/api/v3/data_quality_checks/{organization_id}/start/',
        headers=header,
        json=payload
    )
    check_status(result, partmsg, log)
    data_quality_id = result.json()['progress']['unique_id']

    # perform the data quality check
    print('API Function: perform_data_quality_check\n')
    partmsg = 'perform_data_quality_check'
    params = {
        'organization_id': organization_id,
        'run_id': data_quality_id
    }
    result = requests.get(
        main_url + '/api/v3/data_quality_checks/results/',
        headers=header,
        params=params
    )
    check_status(result, partmsg, log)


def export_data(header, main_url, organization_id, log):

    # Get IDs for some properties
    num_props = 25
    params = {
        'organization_id': organization_id,
        'page': 1,
        'per_page': 999999999
    }
    result = requests.post(main_url + '/api/v3/properties/filter/',
                           headers=header,
                           params=params)
    prop_ids = [prop['property_view_id'] for prop in result.json()['results']]
    prop_ids = prop_ids[:num_props]

    print('API Function: export_properties\n')
    partmsg = 'export_properties'
    params = {
        'organization_id': organization_id,
        'inventory_type': 'properties'
    }
    payload = {
        'ids': prop_ids,
        'filename': 'test_seed_host_api---properties-export.csv',
        'profile_id': None,
        'export_type': 'csv',
    }
    result = requests.post(main_url + '/api/v3/tax_lot_properties/export/',
                           headers=header,
                           params=params,
                           json=payload)
    check_status(result, partmsg, log, piid_flag='export')

    # Get IDs for some taxlots
    num_lots = 25
    params = {
        'organization_id': organization_id,
        'page': 1,
        'per_page': 999999999
    }
    result = requests.post(main_url + '/api/v3/taxlots/filter/',
                           headers=header,
                           params=params)
    lot_ids = [lot['taxlot_view_id'] for lot in result.json()['results']]
    lot_ids = lot_ids[:num_lots]

    print('API Function: export_taxlots\n')
    partmsg = 'export_taxlots'
    params = {
        'organization_id': organization_id,
        'inventory_type': 'taxlots'
    }
    payload = {
        'ids': lot_ids,
        'filename': 'test_seed_host_api---taxlots-export.csv',
        'profile_id': None,
        'export_type': 'csv',
    }
    result = requests.post(main_url + '/api/v3/tax_lot_properties/export/',
                           headers=header,
                           params=params,
                           json=payload)
    check_status(result, partmsg, log, piid_flag='export')
