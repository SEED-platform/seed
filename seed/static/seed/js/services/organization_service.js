/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// organization services
angular.module('BE.seed.service.organization', []).factory('organization_service', [
  '$http',
  '$q',
  'generated_urls',
  function ($http, $q, generated_urls) {

    var organization_factory = { total_organizations_for_user: 0 };
    // until we switch to replacing ``urls`` everywhere with generated URLs
    var urls = generated_urls;

    organization_factory.get_organizations = function() {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/'
        }).success(function(data, status, headers, config) {
            organization_factory.total_organizations_for_user = (data.organizations !== undefined ) ? data.organizations.length : 0;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);

        });
        return defer.promise;
    };

    organization_factory.add = function(org) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            url: '/api/v2/organizations/',
            data: {user_id: org.email.user_id, organization_name: org.name}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    organization_factory.get_organization_users = function(org) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/' + org.org_id + '/users/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    organization_factory.add_user_to_org = function(org_user) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: '/api/v2/organizations/' + org_user.organization.org_id + '/add_user/',
            data: {user_id: org_user.user.user_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    organization_factory.remove_user = function(user_id, org_id) {
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: '/api/v2/organizations/' + org_user.organization.org_id + '/remove_user/',
            data: {user_id: user_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    organization_factory.get_organization = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/' + org_id + '/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * updates the role for a user within an org
     * @param  {int} user_id id of user
     * @param  {int} org_id  id of organization
     * @param  {str} role    role
     * @return {promise obj}         promise object
     */
    organization_factory.update_role = function(user_id, org_id, role) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: '/api/v2/users/' + user_id + '/update_role/',
            data: {
                organization_id: org_id,
                role: role
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * saves the organization settings
     * @param  {obj} org an organization with fields to share between sub-orgs
     */
    organization_factory.save_org_settings = function(org) {
        var defer = $q.defer();
        org.organization_id = org.id;
        $http({
            method: 'PUT',
            url: '/api/v2/organizations/' + org.id + '/save_settings/',
            data: {
                organization_id: org.id,
                organization: org
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * gets the shared fields for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_shared_fields = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/' + org_id + '/shared_fields/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_query_threshold = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/' + org_id + '/query_threshold/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * gets the data cleansing rules for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.get_cleansing_rules = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/organizations/' + org_id + '/cleansing_rules/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * resets the default data cleansing rules for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.reset_cleansing_rules = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: '/api/v2/organizations/' + org_id + '/reset_cleansing_rules/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * saves the organization data cleansing rules
     * @param  {int} org_id the id of the organization
     * @param  {obj} cleansing_rules the updated rules to save
     */
    organization_factory.save_cleansing_rules = function(org_id, cleansing_rules) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: '/api/v2/organizations/' + org_id + '/save_cleansing_rules/',
            data: {
                cleansing_rules: cleansing_rules
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * gets the query threshold for an org
     * @param  {int} org_id the id of the organization
     */
    organization_factory.create_sub_org = function(parent_org, sub_org) {
        var defer = $q.defer();
        console.log(sub_org);
        $http({
            method: 'POST',
            url: '/api/v2/organizations/' + parent_org.id + '/sub_org/',
            data: {
                sub_org_name: sub_org.name, sub_org_owner_email: sub_org.email
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    organization_factory.delete_organization_buildings = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: window.BE.urls.delete_organization_buildings,
            params: {
                org_id: org_id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);

        });
        return defer.promise;
    };

    organization_factory.delete_organization = function(org_id) {
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: '/api/v2/organizations/' + org_id + '/'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);

        });
        return defer.promise;
    };

    return organization_factory;
}]);
