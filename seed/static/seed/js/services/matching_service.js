/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// matching services
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  'user_service',
  'generated_urls',
  'spinner_utility',
  function ($http, user_service, generated_urls, spinner_utility) {

    var matching_factory = {};

    /**
     *Start system matching
     *
     *@param import_file_id: int, the database id of the import file
     * we wish to match against other buildings for an organization.
     */
    matching_factory.start_system_matching = function (import_file_id) {
      return $http.post('/api/v2/import_files/' + import_file_id + '/start_system_matching/', {
        organization_id: user_service.get_organization().id
      }).then(function (response) {
        return response.data;
      });
    };

    matching_factory.available_matches = function (import_file_id, inventory_type, state_id) {
      return $http.post('/api/v2/import_files/' + import_file_id + '/available_matches/', {
        inventory_type: inventory_type,
        state_id: state_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    matching_factory.unmatch = function (import_file_id, inventory_type, state_id, coparent_id) {
      spinner_utility.show();
      return $http.post('/api/v2/import_files/' + import_file_id + '/unmatch/', {
        inventory_type: inventory_type,
        state_id: state_id,
        coparent_id: coparent_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_factory.match = function (import_file_id, inventory_type, state_id, matching_state_id) {
      spinner_utility.show();
      return $http.post('/api/v2/import_files/' + import_file_id + '/match/', {
        inventory_type: inventory_type,
        state_id: state_id,
        matching_state_id: matching_state_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_factory.saveVisibility = function (matchingVisibility) {
      var key = 'matchingVisibility.' + user_service.get_organization().id;
      localStorage.setItem(key, matchingVisibility);
    };

    matching_factory.loadVisibility = function () {
      var key = 'matchingVisibility.' + user_service.get_organization().id;
      return localStorage.getItem(key) || 'Show All';
    };

    return matching_factory;
  }]);
