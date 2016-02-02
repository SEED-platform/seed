/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// matching services
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  'generated_urls',
  function ($http, $q, $timeout, user_service, generated_urls) {

    var matching_factory = {};

    function api_success_fn(defer) {
      return function (data, status, headers, config) {
        defer.resolve(data);
      };
    }

    function api_error_fn(defer) {
      return function (data, status, headers, config) {
        defer.reject(data, status);
      };
    }

    function api_request(http_info, success_fn, error_fn) {
      var defer = $q.defer();
      var on_success, on_error;
      if (!success_fn) {
        on_success = api_success_fn(defer);
      } else {
        on_success = success_fn(defer);
      }

      if (!error_fn) {
        on_error = api_error_fn(defer);
      } else {
        on_error = error_fn(defer);
      }

      $http(http_info).success(on_success).error(on_error);
      return defer.promise;
    }

    /*
     *Start system matching
     *
     *@param import_file_id: int, the database id of the import file
     * we wish to match against other buildings for an organization.
     */
    matching_factory.start_system_matching = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.start_system_matching,
            'data': {
                'file_id': import_file_id,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);

        });
        return defer.promise;
    };

    matching_factory.get_match_nodes = function ( building_id ) {
        return api_request({
            method: 'GET',
            url: generated_urls.seed.get_relevant_nodes,
            params: {
                organization_id: user_service.get_organization().id,
                building_id: building_id
            }
        });
    };

    matching_factory.get_match_tree = function( building_id ) {
        return api_request({
            method: 'GET',
            'url': generated_urls.seed.get_coparents,
            'params': {
                'organization_id': user_service.get_organization().id,
                'building_id': building_id
            }
        }, function (defer) {
          return function (data, status, headers, config) {
            data.match_tree.map(function (b) {
              b.matches_current = true;
            });
            data.coparents.map(function (b) {
              b.matches_current = true;
            });
            defer.resolve(data);
          };
        });
    };

   return matching_factory;
}]);
