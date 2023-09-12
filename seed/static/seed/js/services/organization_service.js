/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.organization', []).factory('organization_service', [
  '$http',
  '$q',
  '$timeout',
  'naturalSort',
  function ($http, $q, $timeout, naturalSort) {

    var organization_factory = {total_organizations_for_user: 0};

    organization_factory.get_organizations = function () {
      return $http.get('/api/v3/organizations/').then(function (response) {
        organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
        response.data.organizations = response.data.organizations.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });
        return response.data;
      });
    };

    organization_factory.get_organizations_brief = function () {
      return $http.get('/api/v3/organizations/', {
        params: {
          brief: true
        }
      }).then(function (response) {
        organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
        response.data.organizations = response.data.organizations.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });
        return response.data;
      });
    };

    organization_factory.add = function (org) {
      return $http.post('/api/v3/organizations/', {
        user_id: org.email.user_id,
        organization_name: org.name
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_organization_users = function (org) {
      return $http.get('/api/v3/organizations/' + org.org_id + '/users/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.add_user_to_org = function (org_user) {
      return $http.put(
        '/api/v3/organizations/' + org_user.organization.org_id + '/users/' + org_user.user.user_id + '/add/'
      ).then(function (response) {
        return response.data;
      });
    };

    organization_factory.remove_user = function (user_id, org_id) {
      return $http.delete(
        '/api/v3/organizations/' + org_id + '/users/' + user_id + '/remove/'
      ).then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_organization = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_organization_brief = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/', {
        params: {
          brief: true
        }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * updates the role for a user within an org
     * @param  {int} user_id id of user
     * @param  {int} org_id  id of organization
     * @param  {str} role    role
     * @return {promise obj}         promise object
     */
    organization_factory.update_role = function (user_id, org_id, role) {
      return $http.put('/api/v3/users/' + user_id + '/role/', {
        role: role
      }, {
        params: { organization_id: org_id }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * saves the organization settings
     * @param  {obj} org an organization with fields to share between sub-orgs
     */
    organization_factory.save_org_settings = function (org) {
      org.organization_id = org.id;
      return $http.put('/api/v3/organizations/' + org.id + '/save_settings/', {
        organization_id: org.id,
        organization: org
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the shared fields for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_shared_fields = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/shared_fields/').then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_query_threshold = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/query_threshold/').then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.create_sub_org = function (parent_org, sub_org) {
      return $http.post('/api/v3/organizations/' + parent_org.id + '/sub_org/', {
        sub_org_name: sub_org.name,
        sub_org_owner_email: sub_org.email
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.delete_organization_inventory = function (org_id) {
      return $http.delete(
        '/api/v3/organizations/' + org_id + '/inventory/'
      ).then(function (response) {
        return response.data;
      });
    };

    organization_factory.delete_organization = function (org_id) {
      return $http.delete('/api/v3/organizations/' + org_id + '/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.matching_criteria_columns = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/matching_criteria_columns/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.match_merge_link = function (org_id, inventory_type) {
      return $http.post('/api/v3/organizations/' + org_id + '/match_merge_link/', {
        inventory_type: inventory_type
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.geocoding_columns = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/geocoding_columns/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.match_merge_link_preview = function (org_id, inventory_type, criteria_change_columns) {
      return $http.post('/api/v3/organizations/' + org_id + '/match_merge_link_preview/', {
        inventory_type: inventory_type,
        add: criteria_change_columns.add,
        remove: criteria_change_columns.remove
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_match_merge_link_result = function (org_id, match_merge_link_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/match_merge_link_result/' + '?match_merge_link_id=' + match_merge_link_id).then(function (response) {
        return response.data;
      });
    };

    organization_factory.check_match_merge_link_status = function (progress_key) {
      var deferred = $q.defer();
      checkStatusLoop(deferred, progress_key);
      return deferred.promise;
    };

    organization_factory.reset_all_passwords = function (org_id) {
      return $http.post('/api/v3/organizations/' + org_id + '/reset_all_passwords/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.insert_sample_data = function (org_id) {
      return $http.get('/api/v3/organizations/' + org_id + '/insert_sample_data/').then(function (response) {
        return response.data;
      });
    };

    var checkStatusLoop = function (deferred, progress_key) {
      $http.get('/api/v3/progress/' + progress_key + '/').then(function (response) {
        $timeout(function () {
          if (response.data.progress < 100) {
            checkStatusLoop(deferred, progress_key);
          } else {
            deferred.resolve(response.data);
          }
        }, 750);
      }, function (error) {
        deferred.reject(error);
      });
    };

    /**
     * Returns the display value for an inventory
     * @param  {object} { property_display_field, taxlot_display_field }, organization object
     * @param  {string} inventory_type 'property' or 'taxlot'
     * @param  {object} inventory_state state object of the inventory
     */
    organization_factory.get_inventory_display_value = function ({ property_display_field, taxlot_display_field }, inventory_type, inventory_state) {
      const field = inventory_type === 'property' ? property_display_field : taxlot_display_field;
      if (field == null) {
        throw Error(`Provided display field for type "${inventory_type}" is undefined`);
      }
      // if nothing is returned, check in extra data
      let return_field = inventory_state[field];
      if (return_field == null) {
        console.log("field: ", field);
        console.log('inventory state extra data: ', inventory_state);
        if (field in inventory_state.extra_data) {
          return_field = inventory_state.extra_data[field];
        }
      }

      return return_field;
    };

    return organization_factory;
  }]);
