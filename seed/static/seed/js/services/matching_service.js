/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
      return $http.post('/api/v3/import_files/' + import_file_id + '/start_system_matching_and_geocoding/', {},
        {
          params: { organization_id: user_service.get_organization().id }
        }).then(function (response) {
        return response.data;
      }).catch(function (e) {
        return e.data;
      });
    };

    matching_service.mergeProperties = function (property_view_ids) {
      spinner_utility.show();
      return $http.post('/api/v3/properties/merge/', {
        property_view_ids
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
      return $http.put('/api/v3/properties/' + view_id + '/unmerge/', {}, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_service.mergeTaxlots = function (taxlot_view_ids) {
      spinner_utility.show();
      return $http.post('/api/v3/taxlots/merge/', {
        taxlot_view_ids
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
      return $http.post('/api/v3/taxlots/' + view_id + '/unmerge/', {}, {
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
