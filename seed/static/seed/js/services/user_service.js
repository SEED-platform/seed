/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// user services
angular.module('BE.seed.service.user', []).factory('user_service', [
  '$http',
  '$q',
  'generated_urls',
  function ($http, $q, generated_urls) {
    var user_factory = {};
    var urls = generated_urls;

    var organization;
    var user_id;

    /**
     * returns the current organization, set initially by a controller
     * @return {obj} organization
     */
    user_factory.get_organization = function() {
        // yes this is a global, but otherwise we'll have to use a promise in
        // front of every request that needs this. window.config.initial_org_id is
        // set in base.html via the seed.views.main home view
        return organization || {
            id: window.BE.initial_org_id,
            name: window.BE.initial_org_name,
            user_role: window.BE.initial_org_user_role

        };
    };

    /**
     * sets the current organization
     * @param {obj} org
     * @return {promise}
     */
    user_factory.set_organization = function(org) {
        organization = org;
        var defer = $q.defer();
        user_factory.get_user_id().then(function (this_user_id) {
            $http({
                method: 'PUT',
                url: '/api/v2/users/' + this_user_id.toString() + '/default_organization/',
                data: {
                    organization_id: org.id
                }
            }).success(function (data) {
                defer.resolve(data);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        });
        return defer.promise;
    };

    user_factory.get_users = function() {

        var defer = $q.defer();
        $http.get('/api/v2/users/').success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    user_factory.add = function(user) {
        var defer = $q.defer();

        var new_user_details = {first_name: user.first_name,
                                last_name: user.last_name,
                                email: user.email,
                                org_name: user.org_name,
                                role: user.role
                               };

        if (!_.isUndefined(user.organization)) {
            new_user_details.organization_id = user.organization.org_id;
        }

        $http({
            method: 'POST',
            url: '/api/v2/users/',
            data: new_user_details
        }).success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /* Is this still needed? */
    user_factory.get_default_columns = function() {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: urls.seed.get_default_columns
        }).success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    user_factory.get_default_building_detail_columns = function() {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: urls.seed.get_default_building_detail_columns
        }).success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    user_factory.get_shared_buildings = function() {
        var defer = $q.defer();
        user_factory.get_user_id().then(function (this_user_id) {
            $http({
                method: 'GET',
                url: '/api/v2/users/' + this_user_id + '/shared_buildings/'
            }).success(function (data) {
                defer.resolve(data);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        });
        return defer.promise;
    };

    /**
     * gets the user's first name, last name, email, and API key if exists
     * @return {obj} object with keys: first_name, last_name, email, api_key
     */
    user_factory.get_user_profile = function() {
        var defer = $q.defer();
        user_factory.get_user_id().then(function (this_user_id) {
            $http({
                method: 'GET',
                url: '/api/v2/users/' + this_user_id.toString() + '/'
            }).success(function (data) {
                defer.resolve(data);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        });
        return defer.promise;
    };

    /**
     * asks the server to generate a new API key
     * @return {obj} object with api_key
     */
    user_factory.generate_api_key = function() {
        var defer = $q.defer();
        user_factory.get_user_id().then(function (this_user_id) {
            $http({
                method: 'GET',
                url: '/api/v2/users/' + this_user_id.toString() + '/generate_api_key/'
            }).success(function (data) {
                defer.resolve(data);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        });
        return defer.promise;
    };

    user_factory.set_default_columns = function(columns, show_shared_buildings) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            url: urls.seed.set_default_columns,
            data: {columns: columns, show_shared_buildings: show_shared_buildings}
        }).success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    user_factory.set_default_building_detail_columns = function(columns) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            url: urls.seed.set_default_building_detail_columns,
            data: {columns: columns}
        }).success(function(data) {
            defer.resolve(data);
        }).error(function(data, status) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * updates the user's PR
     * @param  {obj} user
     */
    user_factory.update_user = function(user) {
        var defer = $q.defer();
            user_factory.get_user_id().then(function (this_user_id) {
                $http({
                    method: 'PUT',
                    url: '/api/v2/users/' + this_user_id.toString() + '/',
                    data: {
                        first_name: user.first_name,
                        last_name: user.last_name,
                        email: user.email
                    }
                }).success(function (data) {
                    defer.resolve(data);
                }).error(function (data, status) {
                    defer.reject(data, status);
                });
            });
        return defer.promise;
    };

    /**
     * sets the user's password
     * @param {string} current_password
     * @param {string} password_1
     * @param {string} password_2
     */
    user_factory.set_password = function(current_password, password_1, password_2) {
        var defer = $q.defer();
        user_factory.get_user_id().then(function (this_user_id) {
            $http({
                method: 'PUT',
                url: '/api/v2/users/' + this_user_id.toString() + '/set_password/',
                data: {
                    current_password: current_password,
                    password_1: password_1,
                    password_2: password_2
                }
            }).success(function (data) {
                defer.resolve(data);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        });
        return defer.promise;
    };

    /**
     * gets the current user's id
     */
    user_factory.get_user_id = function () {
        var defer = $q.defer();
        if (!_.isNil(user_id)) defer.resolve(user_id);
        else {
            $http.get('/api/v2/users/current_user_id/').success(function (data) {
                user_id = data.pk;
                defer.resolve(user_id);
            }).error(function (data, status) {
                defer.reject(data, status);
            });
        }
        return defer.promise;
    };

    return user_factory;
}]);
