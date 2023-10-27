/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.organization', []).factory('organization_service', [
  '$http',
  '$q',
  '$timeout',
  'naturalSort',
  ($http, $q, $timeout, naturalSort) => {
    const organization_factory = { total_organizations_for_user: 0 };

    organization_factory.get_organizations = () => $http.get('/api/v3/organizations/').then((response) => {
      organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
      response.data.organizations = response.data.organizations.sort((a, b) => naturalSort(a.name, b.name));
      return response.data;
    });

    organization_factory.get_organizations_brief = () => $http
      .get('/api/v3/organizations/', {
        params: {
          brief: true
        }
      })
      .then((response) => {
        organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
        response.data.organizations = response.data.organizations.sort((a, b) => naturalSort(a.name, b.name));
        return response.data;
      });

    organization_factory.add = (org) => $http
      .post('/api/v3/organizations/', {
        user_id: org.email.user_id,
        organization_name: org.name
      })
      .then((response) => response.data);

    organization_factory.get_organization_users = (org) => $http.get(`/api/v3/organizations/${org.org_id}/users/`).then((response) => response.data);

    organization_factory.add_user_to_org = (org_user) => $http.put(`/api/v3/organizations/${org_user.organization.org_id}/users/${org_user.user.user_id}/add/`).then((response) => response.data);

    organization_factory.remove_user = (user_id, org_id) => $http.delete(`/api/v3/organizations/${org_id}/users/${user_id}/remove/`).then((response) => response.data);

    organization_factory.get_organization = (org_id) => $http.get(`/api/v3/organizations/${org_id}/`).then((response) => response.data);

    organization_factory.get_organization_brief = (org_id) => $http
      .get(`/api/v3/organizations/${org_id}/`, {
        params: {
          brief: true
        }
      })
      .then((response) => response.data);

    organization_factory.get_organization_access_level_tree = (org_id) => $http.get(`/api/v3/organizations/${org_id}/` + 'access_levels/tree').then((response) => response.data);

    organization_factory.update_organization_access_level_names = (org_id, new_access_level_names) => $http.post(
      `/api/v3/organizations/${org_id}/` + 'access_levels/access_level_names/',
      { access_level_names: new_access_level_names }
    ).then((response) => response.data);

    organization_factory.can_delete_access_level_instance = (org_id, instance_id) => {
      return $http.get('/api/v3/organizations/' + org_id + '/' + 'access_levels/' + instance_id + '/can_delete_instance/',
      ).then(function (response) {
        return response.data;
      });
    };

    organization_factory.delete_access_level_instance = (org_id, instance_id) => {
      return $http.delete('/api/v3/organizations/' + org_id + '/' + 'access_levels/' + instance_id + '/delete_instance/',
      ).then(function (response) {
        return response.data;
      });
    };

    organization_factory.create_organization_access_level_instance = (org_id, parent_id, name) => $http.post(
      `/api/v3/organizations/${org_id}/` + 'access_levels/add_instance/',
      { parent_id, name }
    ).then((response) => response.data);

    organization_factory.edit_organization_access_level_instance = (org_id, instance_id, name) => $http.patch(
      `/api/v3/organizations/${org_id}/` + `access_levels/${instance_id}/edit_instance/`,
      { name }
    ).then((response) => response.data);

    /**
     * updates the role for a user within an org
     * @param  {int} user_id id of user
     * @param  {int} org_id  id of organization
     * @param  {str} role    role
     * @return {promise obj}         promise object
     */
    organization_factory.update_role = (user_id, org_id, role) => $http
      .put(
        `/api/v3/users/${user_id}/role/`,
        {
          role
        },
        {
          params: { organization_id: org_id }
        }
      )
      .then((response) => response.data);

    /**
     * saves the organization settings
     * @param  {obj} org an organization with fields to share between sub-orgs
     */
    organization_factory.save_org_settings = (org) => {
      org.organization_id = org.id;
      return $http
        .put(`/api/v3/organizations/${org.id}/save_settings/`, {
          organization_id: org.id,
          organization: org
        })
        .then((response) => response.data);
    };

    /**
     * gets the shared fields for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_shared_fields = (org_id) => $http.get(`/api/v3/organizations/${org_id}/shared_fields/`).then((response) => response.data);

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_query_threshold = (org_id) => $http.get(`/api/v3/organizations/${org_id}/query_threshold/`).then((response) => response.data);

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.create_sub_org = (parent_org, sub_org) => $http
      .post(`/api/v3/organizations/${parent_org.id}/sub_org/`, {
        sub_org_name: sub_org.name,
        sub_org_owner_email: sub_org.email
      })
      .then((response) => response.data);

    organization_factory.delete_organization_inventory = (org_id) => $http.delete(`/api/v3/organizations/${org_id}/inventory/`).then((response) => response.data);

    organization_factory.delete_organization = (org_id) => $http.delete(`/api/v3/organizations/${org_id}/`).then((response) => response.data);

    organization_factory.matching_criteria_columns = (org_id) => $http.get(`/api/v3/organizations/${org_id}/matching_criteria_columns/`).then((response) => response.data);

    organization_factory.geocoding_columns = (org_id) => $http.get(`/api/v3/organizations/${org_id}/geocoding_columns/`).then((response) => response.data);

    organization_factory.reset_all_passwords = (org_id) => $http.post(`/api/v3/organizations/${org_id}/reset_all_passwords/`).then((response) => response.data);

    organization_factory.insert_sample_data = (org_id) => $http.get(`/api/v3/organizations/${org_id}/insert_sample_data/`).then((response) => response.data);

    /**
     * Returns the display value for an inventory
     * @param  {object} { property_display_field, taxlot_display_field }, organization object
     * @param  {string} inventory_type 'property' or 'taxlot'
     * @param  {object} inventory_state state object of the inventory
     */
    organization_factory.get_inventory_display_value = ({ property_display_field, taxlot_display_field }, inventory_type, inventory_state) => {
      const field = inventory_type === 'property' ? property_display_field : taxlot_display_field;
      if (field == null) {
        throw Error(`Provided display field for type "${inventory_type}" is undefined`);
      }
      // if nothing is returned, check in extra data
      let return_field = inventory_state[field];
      if (return_field == null) {
        if (field in inventory_state.extra_data) {
          return_field = inventory_state.extra_data[field];
        }
      }

      return return_field;
    };

    return organization_factory;
  }
]);
