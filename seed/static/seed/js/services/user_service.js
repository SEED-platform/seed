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
    user_factory.get_organization = function () {
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
    user_factory.set_organization = function (org) {
      organization = org;
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.put('/api/v2/users/' + this_user_id + '/default_organization/', {
          organization_id: org.id
        }).then(function (response) {
          return response.data;
        });
      });
    };

    user_factory.get_users = function () {
      return $http.get('/api/v2/users/').then(function (response) {
        return response.data;
      });
    };

    user_factory.add = function (user) {
      var new_user_details = {
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        org_name: user.org_name,
        role: user.role
      };

      if (!_.isUndefined(user.organization)) {
        new_user_details.organization_id = user.organization.org_id;
      }

      return $http.post('/api/v2/users/', new_user_details).then(function (response) {
        return response.data;
      });
    };

    /* Is this still needed? */
    user_factory.get_default_columns = function () {
      return $http.get(urls.seed.get_default_columns).then(function (response) {
        return response.data;
      });
    };

    user_factory.get_default_building_detail_columns = function () {
      return $http.get(urls.seed.get_default_building_detail_columns).then(function (response) {
        return response.data;
      });
    };

    user_factory.get_shared_buildings = function () {
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.get('/api/v2/users/' + this_user_id + '/shared_buildings/').then(function (response) {
          return response.data;
        });
      });
    };

    /**
     * gets the user's first name, last name, email, and API key if exists
     * @return {obj} object with keys: first_name, last_name, email, api_key
     */
    user_factory.get_user_profile = function () {
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.get('/api/v2/users/' + this_user_id + '/').then(function (response) {
          return response.data;
        });
      });
    };

    /**
     * asks the server to generate a new API key
     * @return {obj} object with api_key
     */
    user_factory.generate_api_key = function () {
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.get('/api/v2/users/' + this_user_id + '/generate_api_key/').then(function (response) {
          return response.data;
        });
      });
    };

    user_factory.set_default_columns = function (columns, show_shared_buildings) {
      return $http.post(urls.seed.set_default_columns, {
        columns: columns,
        show_shared_buildings: show_shared_buildings
      }).then(function (response) {
        return response.data;
      });
    };

    user_factory.set_default_building_detail_columns = function (columns) {
      return $http.post(urls.seed.set_default_building_detail_columns, {
        columns: columns
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * updates the user's PR
     * @param  {obj} user
     */
    user_factory.update_user = function (user) {
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.put('/api/v2/users/' + this_user_id + '/', {
          first_name: user.first_name,
          last_name: user.last_name,
          email: user.email
        }).then(function (response) {
          return response.data;
        });
      });
    };

    /**
     * sets the user's password
     * @param {string} current_password
     * @param {string} password_1
     * @param {string} password_2
     */
    user_factory.set_password = function (current_password, password_1, password_2) {
      return user_factory.get_user_id().then(function (this_user_id) {
        return $http.put('/api/v2/users/' + this_user_id + '/set_password/', {
          current_password: current_password,
          password_1: password_1,
          password_2: password_2
        }).then(function (response) {
          return response.data;
        });
      });
    };

    /**
     * gets the current user's id
     */
    user_factory.get_user_id = function () {
      if (_.isUndefined(user_id)) {
        user_id = $http.get('/api/v2/users/current_user_id/').then(function (response) {
          return response.data.pk;
        });
      }
      return user_id;
    };

    return user_factory;
  }]);
