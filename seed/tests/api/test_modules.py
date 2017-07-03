# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime as dt
import json
import pprint
import time

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
    print ('API Function: upload_file\n'),
    partmsg = 'upload_file'
    result = upload_file(header, filepath, main_url, dataset_id, filetype)
    check_status(result, partmsg, log)

    # Get import ID
    import_id = result.json()['import_file_id']

    # Save the data to BuildingSnapshots
    print('API Function: save_raw_data\n'),
    partmsg = 'save_raw_data'
    payload = {
        'organization_id': organization_id,
        'cycle_id': cycle_id
    }
    result = requests.post(
        main_url + '/api/v2/import_files/{}/save_raw_data/'.format(import_id),
        headers=header,
        json=payload
    )
    check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Get the mapping suggestions
    print('API Function: get_column_mapping_suggestions\n'),
    partmsg = 'get_column_mapping_suggestions'
    result = requests.get(
        main_url + '/api/v2/import_files/{}/mapping_suggestions/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header)
    check_status(result, partmsg, log, piid_flag='mappings')

    # Save the column mappings
    print('API Function: save_column_mappings\n'),
    partmsg = 'save_column_mappings'
    payload = {'mappings': read_map_file(mappingfilepath)}
    result = requests.post(
        main_url + '/api/v2/import_files/{}/save_column_mappings/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header,
        json=payload
    )
    check_status(result, partmsg, log)

    # Perform mapping
    print('API Function: perform_mapping\n'),
    partmsg = 'save_column_mappings'
    result = requests.post(
        main_url + '/api/v2/import_files/{}/perform_mapping/'.format(import_id),
        params={"organization_id": organization_id},
        headers=header
    )
    check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Get Data Quality Message
    print ('API Function: data_quality\n'),
    partmsg = 'data_quality'

    result = requests.get(
        main_url + '/api/v2/import_files/{}/data_quality_results/'.format(import_id),
        headers=header,
        params={"organization_id": organization_id}
    )
    check_status(result, partmsg, log, piid_flag='data_quality')

    # Match uploaded buildings with buildings already in the organization.
    print ('API Function: start_system_matching\n'),
    partmsg = 'start_system_matching'
    payload = {'file_id': import_id, 'organization_id': organization_id}

    result = requests.post(
        main_url + '/api/v2/import_files/{}/start_system_matching/'.format(import_id),
        headers=header,
        params={"organization_id": organization_id},
        json=payload
    )
    result = check_progress(main_url, header, result.json()['progress_key'])
    check_status(result, partmsg, log)

    # Check number of matched and unmatched BuildingSnapshots
    print ('API Function: matching_results\n'),
    partmsg = 'matching_results'

    result = requests.get(
        main_url + '/api/v2/import_files/{}/matching_results/'.format(import_id),
        headers=header,
        params={})
    check_status(result, partmsg, log)


def search_and_project(header, main_url, organization_id, log):
    # Search CanonicalBuildings
    print ('API Function: search_buildings\n'),
    partmsg = 'search_buildings'
    search_payload = {'filter_params': {u'address_line_1': u'94734 SE Honeylocust Street'}}

    result = requests.get(main_url + '/app/search_buildings/',
                          headers=header,
                          data=json.dumps(search_payload))
    check_status(result, partmsg, log)

    # Project
    print ('\n-------Project-------\n')

    # Create a Project for 'Condo' in 'use_description'
    print ('API Function: create_project\n'),
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
    print ('API Function: get_project\n'),
    partmsg = 'get_project'

    result = requests.get(main_url + '/api/v2/projects/',
                          headers=header,
                          params=json.dumps(
                              {'project_slug': project_slug, 'organization_id': organization_id}))
    check_status(result, partmsg, log)

    # Populate project by search buildings result
    print ('API Function: add_buildings_to_project\n'),
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

    # Export
    print ('\n-------Export-------\n')

    # Export all buildings.
    print ('API Function: export_buildings\n'),
    partmsg = 'export_buildings'
    export_payload = {'export_name': 'project_buildings',
                      'export_type': "csv",
                      'select_all_checkbox': True,
                      'filter_params': {'project__slug': project_slug}}

    result = requests.post(main_url + '/app/export_buildings/',
                           headers=header,
                           data=json.dumps(export_payload))
    check_status(result, partmsg, log)
    if result.json()['total_buildings'] != 58:
        log.warning('Export Buildings: ' + str(result.json()['total_buildings']) + " ; expected 58")

        # Get exportID
    exportID = result.json()['export_id']

    progress = requests.post(main_url + '/app/export_buildings/progress/',
                             headers=header,
                             data=json.dumps({'export_id': exportID}))
    log.debug(pprint.pformat(progress.json()))

    print ('API Function: export_buildings_download\n'),
    partmsg = 'export_buildings_download'

    count = 100
    while (count > 0):
        result = requests.post(main_url + '/app/export_buildings/download/',
                               headers=header,
                               data=json.dumps({'export_id': exportID}))
        if result.status_code == 200:
            break
        time.sleep(5)
        count -= 1

    check_status(result, partmsg, log)

    return project_slug


def account(header, main_url, username, log):
    # Retrieve the user id key for later retrievals
    print ('API Function: current_user_id\n')
    result = requests.get(
        main_url + '/api/v2/users/current_user_id/',
        headers=header
    )
    user_pk = json.loads(result.content)['pk']

    # Retrieve the user profile
    print ('API Function: get_user_profile\n')
    partmsg = 'get_user_profile'
    result = requests.get(main_url + '/api/v2/users/%s/' % user_pk,
                          headers=header)
    check_status(result, partmsg, log)

    # Retrieve the organizations
    print ('API Function: get_organizations\n'),
    partmsg = 'get_organizations'
    result = requests.get(main_url + '/api/v2/organizations/',
                          headers=header)
    check_status(result, partmsg, log, piid_flag='organizations')

    # # Get the organization id to be used.
    # # NOTE: Loop through the organizations and get the org_id
    # # where the organization owner is 'username' else get the first organization.
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
    mod_url = main_url + '/api/v2/organizations/%s' % str(organization_id)
    result = requests.get(mod_url,
                          headers=header)
    check_status(result, partmsg, log)

    # Change user profile
    # NOTE: Make sure these credentials are ok.
    print ('API Function: update_user\n'),
    partmsg = 'update_user'
    user_payload = {'first_name': 'Sherlock',
                    'last_name': 'Holmes',
                    'email': username}
    result = requests.put(main_url + '/api/v2/users/%s/' % user_pk,
                          headers=header,
                          data=user_payload)
    check_status(result, partmsg, log)

    # Get organization users
    print ('API Function: get_organizations_users\n'),
    partmsg = 'get_organizations_users'
    result = requests.get(main_url + '/api/v2/organizations/%s/users/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log, piid_flag='users')

    # Get organizations settings
    print ('API Function: get_query_treshold\n'),
    partmsg = 'get_query_threshold'
    result = requests.get(main_url + '/api/v2/organizations/%s/query_threshold/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log)

    # Get shared fields
    print ('API Function: get_shared_fields\n'),
    partmsg = 'get_shared_fields'
    result = requests.get(main_url + '/api/v2/organizations/%s/shared_fields/' % organization_id,
                          headers=header)
    check_status(result, partmsg, log)

    return organization_id


def delete_set(header, main_url, organization_id, dataset_id, log):
    # Delete all buildings
    # print ('API Function: delete_inventory\n'),
    # partmsg = 'delete_buildings'
    # result = requests.delete(
    #     main_url + '/app/delete_organization_inventory/',
    #     headers=header,
    #     params={'organization_id': organization_id}
    # )
    # check_status(result, partmsg, log)

    # Delete dataset
    print ('API Function: delete_dataset\n'),
    partmsg = 'delete_dataset'
    result = requests.delete(
        main_url + '/api/v2/datasets/{}/'.format(dataset_id),
        headers=header,
        params={'organization_id': organization_id},
    )
    check_status(result, partmsg, log)

    # Delete project
    # print ('API Function: delete_project\n'),
    # partmsg = 'delete_project'
    # payload = {'organization_id': organization_id,
    #            'project_slug': project_slug}
    #
    # result = requests.delete(main_url + '/app/projects/delete_project/',
    #                          headers=header,
    #                          data=json.dumps(payload))
    # check_status(result, partmsg, log)


def cycles(header, main_url, organization_id, log):
    print ('API Function: get_cycles\n')
    partmsg = 'get_cycles'
    result = requests.get(main_url + '/api/v2/cycles/',
                          headers=header,
                          params={'organization_id': organization_id})
    check_status(result, partmsg, log, piid_flag='cycles')

    cycles = result.json()['cycles']
    print "current cycles are {}".format(cycles)
    for cyc in cycles:
        if cyc['name'] == 'TestCycle':
            cycle_id = cyc['id']
            break
    else:
        # Create cycle (only if it does not exist, until there is a function to delete cycles)
        print ('API Function: create_cycle\n')
        partmsg = 'create_cycle'
        payload = {
            'start': "2015-01-01T08:00",
            'end': "2016-01-01T08:00",
            'name': "TestCycle"
        }
        result = requests.post(main_url + '/api/v2/cycles/',
                               headers=header,
                               params={'organization_id': organization_id},
                               json=payload)
        check_status(result, partmsg, log)

        cycle_id = result.json()['cycles']['id']

    # Update cycle
    print ('\nAPI Function: update_cycle')
    partmsg = 'update_cycle'
    payload = {
        'start': "2015-01-01T08:00",
        'end': "2016-01-01T08:00",
        'name': "TestCycle",
        'id': cycle_id
    }
    result = requests.put(main_url + '/api/v2/cycles/{}/'.format(cycle_id),
                          headers=header,
                          params={'organization_id': organization_id},
                          json=payload)
    check_status(result, partmsg, log)

    # TODO: Test deleting a cycle
    return cycle_id
