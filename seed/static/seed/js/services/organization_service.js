/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// organization services
angular.module('BE.seed.service.organization', []).factory('organization_service', [
  '$http',
  function ($http) {

    var organization_factory = {total_organizations_for_user: 0};

    organization_factory.get_organizations = function () {
      return $http.get('/api/v2/organizations/').then(function (response) {
        organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
        return response.data;
      });
    };

    organization_factory.get_organizations_brief = function () {
      return $http.get('/api/v2/organizations/', {
        params: {
          brief: true
        }
      }).then(function (response) {
        organization_factory.total_organizations_for_user = _.has(response.data.organizations, 'length') ? response.data.organizations.length : 0;
        return response.data;
      });
    };

    organization_factory.add = function (org) {
      return $http.post('/api/v2/organizations/', {
        user_id: org.email.user_id,
        organization_name: org.name
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_organization_users = function (org) {
      return $http.get('/api/v2/organizations/' + org.org_id + '/users/').then(function (response) {
        return response.data;
      });
    };

    organization_factory.add_user_to_org = function (org_user) {
      return $http.put('/api/v2/organizations/' + org_user.organization.org_id + '/add_user/', {
        user_id: org_user.user.user_id
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.remove_user = function (user_id, org_id) {
      return $http.delete('/api/v2/organizations/' + org_id + '/remove_user/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          user_id: user_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.get_organization = function (org_id) {
      return $http.get('/api/v2/organizations/' + org_id + '/').then(function (response) {
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
      return $http.put('/api/v2/users/' + user_id + '/update_role/', {
        organization_id: org_id,
        role: role
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
      return $http.put('/api/v2/organizations/' + org.id + '/save_settings/', {
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
      return $http.get('/api/v2/organizations/' + org_id + '/shared_fields/').then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_query_threshold = function (org_id) {
      return $http.get('/api/v2/organizations/' + org_id + '/query_threshold/').then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the data cleansing rules for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_cleansing_rules = function (org_id) {
      return $http.get('/api/v2/organizations/' + org_id + '/cleansing_rules/').then(function (response) {
        return response.data;
      });
    };

    /**
     * resets the default data cleansing rules for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.reset_cleansing_rules = function (org_id) {
      return $http.put('/api/v2/organizations/' + org_id + '/reset_cleansing_rules/').then(function (response) {
        return response.data;
      });
    };

    /**
     * saves the organization data cleansing rules
     * @param  {int} org_id the id of the organization
     * @param  {obj} cleansing_rules the updated rules to save
     */
    organization_factory.save_cleansing_rules = function (org_id, cleansing_rules) {
      return $http.put('/api/v2/organizations/' + org_id + '/save_cleansing_rules/', {
        cleansing_rules: cleansing_rules
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.create_sub_org = function (parent_org, sub_org) {
      return $http.post('/api/v2/organizations/' + parent_org.id + '/sub_org/', {
        sub_org_name: sub_org.name,
        sub_org_owner_email: sub_org.email
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.delete_organization_inventory = function (org_id) {
      return $http.delete('/app/delete_organization_inventory/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    organization_factory.delete_organization = function (org_id) {
      return $http.delete('/api/v2/organizations/' + org_id + '/').then(function (response) {
        return response.data;
      });
    };

    return organization_factory;
  }]);
