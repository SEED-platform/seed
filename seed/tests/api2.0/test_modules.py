# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime as dt
import json
import pprint
import time

from seed_readingtools import check_progress, check_status, read_map_file, upload_file


def upload_match_sort(header, main_url, organization_id, cycle_id, dataset_id, filepath, filetype,
                      mappingfilepath, log, client):
    # Upload the covered-buildings-sample file
    print ('\nAPI Function: upload_file'),
    partmsg = 'upload_file'

    result = upload_file(header, filepath, main_url, dataset_id, filetype, client)
    check_status(result, partmsg, log)

    header['Content-Type'] = 'application/json'
    # Get import ID
    import_id = result.json()['import_file_id']

    # Get Import file
    print ('\nAPI Function: GET import_files')
    partmsg = 'import_files'
    result = client.get(main_url + '/api/v2/import_files/' + str(import_id),
                        headers=header)
    check_status(result, partmsg, log)

    # Save the data to BuildingSnapshots
    print ('\nAPI Function: save_raw_data'),
    partmsg = 'save_raw_data'
    payload = {'organization_id': organization_id,
               'cycle_id': cycle_id}
    try:
        result = client.post(
            main_url + '/api/v2/import_files/' + str(import_id) + '/save_raw_data/',
            headers=header,
            data=json.dumps(payload))
        check_progress(main_url, header, result.json()['progress_key'], client)
        check_status(result, partmsg, log)
    except:
        log.error("Following API could not be tested")
        return

    # Get first five line
    print ('\nAPI Function: get_first_five_rows')
    partmsg = 'get_first_five_rows'
    try:
        result = client.post(main_url + '/app/get_first_five_rows/',
                             headers=header,
                             data=json.dumps({'import_file_id': import_id}))
        check_status(result, partmsg, log)
    except:
        pass

    # Get imported file
    print ('\nAPI Function: get_import_file'),
    partmsg = 'get_import_file'

    try:
        result = client.get(main_url + '/app/get_import_file/',
                            headers=header,
                            params={'import_file_id': import_id})
        check_status(result, partmsg, log)
    except:
        log.error("Following API could not be tested")
        return

    # Get the mapping suggestions
    print ('\nAPI Function: mapping_suggestions'),
    partmsg = 'mapping_suggestions'
    payload = {'import_file_id': import_id,
               'org_id': organization_id}
    try:
        result = client.get(
            main_url + '/api/v2/data_files/' + str(import_id) + '/mapping_suggestions/',
            headers=header,
            params={'organization_id': organization_id},
            data=json.dumps(payload))
        check_status(result, partmsg, log, PIIDflag='mappings')
    except:
        pass

    # Save the column mappings
    print ('\nAPI Function: save_column_mappings'),
    partmsg = 'save_column_mappings'
    payload = {'import_file_id': import_id,
               'organization_id': organization_id}
    payload['mappings'] = read_map_file(mappingfilepath)
    try:
        result = client.get(main_url + '/app/save_column_mappings/',
                            headers=header,
                            data=json.dumps(payload))
        check_status(result, partmsg, log)
    except:
        log.error("Following API could not be tested")
        return

    # Map the buildings with new column mappings.
    print ('\nAPI Function: remap_buildings'),
    partmsg = 'remap_buildings'
    payload = {'file_id': import_id,
               'organization_id': organization_id}
    try:
        result = client.post(main_url + '/app/remap_buildings/',
                             headers=header,
                             data=json.dumps(payload))

        check_progress(main_url, header, result.json()['progress_key'], client)
        check_status(result, partmsg, log)
    except:
        log.error("Following API could not be tested")
        return

    # Get Data Cleansing Message
    print ('\nAPI Function: cleansing'),
    partmsg = 'cleansing'
    try:
        result = client.get(main_url + '/cleansing/results/',
                            headers=header,
                            params={'import_file_id': import_id})
        check_status(result, partmsg, log, PIIDflag='cleansing')
    except:
        pass

    # Match uploaded buildings with buildings already in the organization.
    print ('\nAPI Function: start_system_matching'),
    partmsg = 'start_system_matching'
    payload = {'file_id': import_id,
               'organization_id': organization_id}
    try:
        result = client.post(main_url + '/app/start_system_matching/',
                             headers=header,
                             data=json.dumps(payload))

        check_progress(main_url, header, result.json()['progress_key'], client)
        check_status(result, partmsg, log)
    except:
        pass

    # Check number of matched and unmatched BuildingSnapshots
    print ('API Function: matching_results\n'),
    partmsg = 'matching_results'

    try:
        result = client.get(main_url + '/api/v2/import_files/' + import_id + 'matching_results/',
                            headers=header,
                            params={})
        check_status(result, partmsg, log, PIIDflag='PM_filter')
    except:
        pass

    return


def search_and_project(header, main_url, organization_id, log, client):
    # Search CanonicalBuildings
    print ('\nAPI Function: search_buildings'),
    partmsg = 'search_buildings'
    search_payload = {'filter_params': {u'address_line_1': u'94734 SE Honeylocust Street'}}
    try:
        result = client.get(main_url + '/app/search_buildings/',
                            headers=header,
                            data=json.dumps(search_payload))
        check_status(result, partmsg, log)
    except:
        pass

    # -- Project
    print ('\n\n-------Project-------')

    # Create a Project for 'Condo' in 'use_description'
    print ('\nAPI Function: create_project'),
    partmsg = 'create_project'
    time1 = dt.datetime.now()
    newproject_payload = {'project': {'name': 'New Project_' + str(time1.day) + str(time1.second),
                                      'compliance_type': 'describe compliance type',
                                      'description': 'project description'},
                          'organization_id': organization_id}
    try:
        result = client.post(main_url + '/app/projects/create_project/',
                             headers=header,
                             data=json.dumps(newproject_payload))
        check_status(result, partmsg, log)
    except:
        log.error("Could not create a project. Following API in SEARCH_AND_PROJECT not tested")
        return

    # Get project slug
    project_slug = result.json()['project_slug']

    # Get the projects for the organization
    print ('\nAPI Function: get_project'),
    partmsg = 'get_project'
    try:
        result = client.get(main_url + '/app/projects/get_projects/',
                            headers=header,
                            params={'organization_id': organization_id})
        check_status(result, partmsg, log)
    except:
        pass

    # Populate project by search buildings result
    print ('\nAPI Function: add_buildings_to_project'),
    partmsg = 'add_buildings_to_project'
    projectbldg_payload = {'project': {'status': 'active',
                                       'project_slug': project_slug,
                                       'slug': project_slug,
                                       'select_all_checkbox': True,
                                       'selected_buildings': [],
                                       'filter_params': {'use_description': 'CONDO'}},
                           'organization_id': organization_id}
    try:
        result = client.post(main_url + '/app/projects/add_buildings_to_project/',
                             headers=header,
                             data=json.dumps(projectbldg_payload))
        time.sleep(20)
        check_status(result, partmsg, log)

        # Get the percent/progress of buildings added to project
        progress = client.post(
            main_url + '/app/projects/get_adding_buildings_to_project_status_percentage/',
            headers=header,
            data=json.dumps(
                {'project_loading_cache_key': result.json()['project_loading_cache_key']}))
        log.debug(pprint.pformat(progress.json()))
    except:
        pass

    # -- Export
    print ('\n\n-------Export-------')

    # Export all buildings.
    print ('\nAPI Function: export_buildings'),
    partmsg = 'export_buildings'
    export_payload = {'export_name': 'project_buildings',
                      'export_type': "csv",
                      'select_all_checkbox': True,
                      'filter_params': {'project__slug': project_slug}}
    try:
        result = client.post(main_url + '/app/export_buildings/',
                             headers=header,
                             data=json.dumps(export_payload))
        check_status(result, partmsg, log)
        if result.json()['total_buildings'] != 58:
            log.warning(
                'Export Buildings: ' + str(result.json()['total_buildings']) + " ; expected 58")

            # Get exportID
        exportID = result.json()['export_id']

        time.sleep(25)
        progress = client.post(main_url + '/app/export_buildings/progress/',
                               headers=header,
                               data=json.dumps({'export_id': exportID}))
        log.debug(pprint.pformat(progress.json()))
        time.sleep(25)

    except:
        log.error("Could not export building. Following API in SEARCH_AND_PROJECT not tested")
        return project_slug

    print ('\nAPI Function: export_buildings_download'),
    partmsg = 'export_buildings_download'
    try:
        result = client.post(main_url + '/app/export_buildings/download/',
                             headers=header,
                             data=json.dumps({'export_id': exportID}))
        check_status(result, partmsg, log)
    except:
        pass

    return project_slug


def label(header, main_url, organization_id, log, client):
    # -- Labels
    print ('\n\n-------Labels-------')

    # Create label
    print ('\nAPI Function: add_label'),
    partmsg = 'add_label'
    label_payload = {'color': 'gray',
                     'label': 'default',
                     'name': 'test label'}
    try:
        result = client.post(main_url + '/app/labels/',
                             headers=header,
                             data=json.dumps(label_payload))
        check_status(result, partmsg, log)
    except:
        log.error("Could not create a label. Following API in LABEL not tested")
        return

    # Get label_id
    label_id = result.json()['id']

    # Get organization labels
    print ('\nAPI Function: get_labels'),
    partmsg = 'get_labels'
    try:
        result = client.get(main_url + '/app/projects/get_labels/',
                            headers=header)
        check_status(result, partmsg, log)
    except:
        pass

    # Apply to buildings that have ENERGY STAR Score > 50
    project_slug = ''
    print ('\nAPI Function: apply_label'),
    partmsg = 'apply_label'
    payload = {'label': {'id': label_id},
               'project_slug': project_slug,
               'buildings': [],
               'select_all_checkbox': True,
               'search_params': {'filter_params': {'project__slug': project_slug}}}
    try:
        result = client.post(main_url + '/app/projects/apply_label/',
                             headers=header,
                             data=json.dumps(payload))
        check_status(result, partmsg, log)
    except:
        pass

    return label_id


def account(header, main_url, username, log, client):
    # Retrieve all users profile [might be only for superuser...]
    #   print ('\nAPI Function: users GET'),
    #   partmsg = 'users_get'
    #   result = client.get(main_url+'/api/v2/users/',
    #                         headers=header)
    #   check_status(result, partmsg, log, PIIDflag='users')

    # Retrieve user id
    print ('\nAPI Function: current_user_id')
    partmsg = 'current_user_id'
    result = client.get(main_url + '/api/v2/users/current_user_id/', headers=header)
    check_status(result, partmsg, log)

    user_id = str(result.json()['pk'])

    # Get the user profile
    print ('\nAPI Function: users/{pk} GET'),
    partmsg = 'users_pk_get'
    result = client.get(main_url + '/api/v2/users/' + user_id + '/', headers=header)
    check_status(result, partmsg, log)

    # Change user profile
    print ('\nAPI Function: users PUT'),
    partmsg = 'users_put'
    user_payload = {
        'first_name': 'Baptiste',
        'last_name': 'Ravache',
        'email': username
    }
    result = client.put(main_url + '/api/v2/users/' + user_id + '/',
                        headers=header,
                        data=json.dumps(user_payload))
    check_status(result, partmsg, log)

    # Retrieve the organizations
    print ('\nAPI Function: organizations'),
    partmsg = 'organizations'
    result = client.get(main_url + '/api/v2/organizations/',
                        headers=header)
    check_status(result, partmsg, log, PIIDflag='organizations')

    # # Get the organization id to be used.
    # # NOTE: Loop through the organizations and get the org_id
    # # where the organization owner is 'username' else get the first organization.
    orgs_result = result.json()
    for ctr in range(len(orgs_result['organizations'])):
        if orgs_result['organizations'][ctr]['owners'][0]['email'] == username:
            organization_id = str(orgs_result['organizations'][ctr]['org_id'])
            break
        else:
            organization_id = str(orgs_result['organizations'][0]['org_id'])

    # Get user authorization
    print ('\nAPI Function: is_authorized'),
    partmsg = 'is_authorized'
    payload = {'actions': ["requires_superuser", "can_invite_member", "can_remove_member",
                           "requires_owner", "requires_member"],
               'organization_id': organization_id}
    result = client.post(main_url + '/api/v2/users/' + user_id + '/is_authorized/',
                         headers=header,
                         params={'organization_id': organization_id},
                         data=json.dumps(payload))
    check_status(result, partmsg, log)

    # Get organizations users
    print ('\nAPI Function: organizations/{pk}/users/')
    partmsg = 'organizations_pk_users'
    result = client.get(main_url + '/api/v2/organizations/' + organization_id + '/users/',
                        headers=header)
    check_status(result, partmsg, log)

    # Get organizations settings
    print ('API Function: query_threshold\n')
    partmsg = 'query_threshold'
    result = client.get(main_url + '/api/v2/organizations/' + organization_id + '/query_threshold/',
                        headers=header)
    check_status(result, partmsg, log)

    # Get shared fields
    print ('\nAPI Function: shared_fields')
    partmsg = 'shared_fields'
    result = client.get(main_url + '/api/v2/organizations/' + organization_id + '/shared_fields/',
                        headers=header)
    check_status(result, partmsg, log)

    id = {'org': organization_id, 'user': user_id}
    return id


def cycles(header, main_url, organization_id, log, client):
    # Get cycles
    print ('API Function: get_cycles\n')
    partmsg = 'get_cycles'
    cycle_name = 'API Test Cycle'
    cycle_id = 138  # horrible idea, but c'est la vie.
    try:
        result = client.get(main_url + '/api/v2/cycles/',
                            headers=header,
                            params={'organization_id': organization_id})
        check_status(result, partmsg, log, PIIDflag='cycles')

        cycles = result.json()['cycles']
        for cyc in cycles:
            if cyc['name'] == cycle_name:
                cycle_id = cyc['id']
                break
        else:
            # Create cycle (only if it doesn't exist, until there is a function to delete cycles)
            print ('API Function: create_cycle\n')
            partmsg = 'create_cycle'
            payload = {
                'start': "2015-01-01T08:00:00.000Z",
                'end': "2016-01-01T08:00:00.000Z",
                'name': cycle_name
            }
            result = client.post(main_url + '/api/v2/cycles/',
                                 headers=header,
                                 params={'organization_id': organization_id},
                                 data=json.dumps(payload))
            check_status(result, partmsg, log)

            cycle_id = result.json()['id']
    except:
        raise Exception("Error getting/creating cycle")

    # Update cycle
    print ('\nAPI Function: update_cycle')
    partmsg = 'update_cycle'
    payload = {
        'start': "2015-01-01T08:00:00.000Z",
        'end': "2016-01-01T08:00:00.000Z",
        'name': cycle_name
    }
    result = client.put(main_url + '/api/v2/cycles/' + str(cycle_id) + '/',
                        headers=header,
                        params={'organization_id': organization_id},
                        data=json.dumps(payload))
    check_status(result, partmsg, log)

    return cycle_id


def delete_set(header, main_url, organization_id, dataset_id, project_slug, log, client):
    # Delete all buildings
    print ('\nAPI Function: delete_buildings'),
    partmsg = 'delete_buildings'
    payload = {'organization_id': organization_id,
               'search_payload': {'select_all_checkbox': True}}
    try:
        result = client.delete(main_url + '/app/delete_buildings/',
                               headers=header,
                               data=json.dumps(payload))
        check_status(result, partmsg, log)
    except:
        print("\n WARNING: Can't delete BUILDING RECORDS, delete manually!")
        input("Press Enter to continue...")

    # Delete dataset
    print ('\nAPI Function: delete_dataset'),
    partmsg = 'delete_dataset'
    try:
        result = client.delete(main_url + '/api/v2/datasets/' + str(dataset_id) + '/',
                               params={'organization_id': organization_id},
                               headers=header)
        check_status(result, partmsg, log)
    except:
        print("\n WARNING: Can't delete BUILDING SET, delete manually!")
        input("Press Enter to continue...")

    # Delete project
    print ('\nAPI Function: delete_project'),
    partmsg = 'delete_project'
    payload = {'organization_id': organization_id,
               'project_slug': project_slug}
    try:
        result = client.delete(main_url + '/app/projects/delete_project/',
                               headers=header,
                               data=json.dumps(payload))
        check_status(result, partmsg, log)
    except:
        print("\n WARNING: Can't delete PROJECT, delete manually!")
        input("Press Enter to continue...")

    # Delete label
    # print ('API Function: delete_label\n'),
    # partmsg = 'delete_label'
    # payload = {'organization_id': organization_id}
    # try:
    #    result = client.delete(main_url+'/app/labels/'+label_id+'/',
    #                             headers = header,
    #                             data=json.dumps(payload))
    #    check_status(result, partmsg, log)
    # except:
    #    print("\n WARNING: Can't delete LABEL, delete manually!")
    #    input("Press Enter to continue...")

    return
