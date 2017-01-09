/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// matching services
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  'user_service',
  'generated_urls',
  function ($http, user_service, generated_urls) {

    var matching_factory = {};

    /*
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

    matching_factory.get_match_nodes = function (building_id) {
      return $http.get(generated_urls.seed.get_relevant_nodes, {
        params: {
          organization_id: user_service.get_organization().id,
          building_id: building_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    matching_factory.get_match_tree = function (building_id) {
      return $http.get(generated_urls.seed.get_coparents, {
        params: {
          organization_id: user_service.get_organization().id,
          building_id: building_id
        }
      }).then(function (response) {
        response.data.match_tree.map(function (b) {
          b.matches_current = true;
        });
        response.data.coparents.map(function (b) {
          b.matches_current = true;
        });
        return response.data;
      });
    };

    return matching_factory;
  }]);
