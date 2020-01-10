/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// matching services
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  'user_service',
  'spinner_utility',
  function ($http, user_service, spinner_utility) {

    var matching_service = {};

    /**
     *Start system matching. For now, geocoding is also kicked off here.
     *
     *@param import_file_id: int, the database id of the import file
     * we wish to match against other buildings for an organization.
     */
    matching_service.start_system_matching = function (import_file_id) {
      return $http.post('/api/v2/import_files/' + import_file_id + '/start_system_matching_and_geocoding/', {
        organization_id: user_service.get_organization().id
      }).then(function (response) {
        return response.data;
      });
    };

    matching_service.mergeProperties = function (state_ids) {
      spinner_utility.show();
      return $http.post('/api/v2/properties/merge/', {
        state_ids: state_ids
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

    matching_service.unmergeProperties = function (view_id) {
      spinner_utility.show();
      return $http.post('/api/v2/properties/' + view_id + '/unmerge/', {}, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_service.mergeTaxlots = function (state_ids) {
      spinner_utility.show();
      return $http.post('/api/v2/taxlots/merge/', {
        state_ids: state_ids
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

    matching_service.unmergeTaxlots = function (view_id) {
      spinner_utility.show();
      return $http.post('/api/v2/taxlots/' + view_id + '/unmerge/', {}, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    return matching_service;
  }]);
