/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// mapping services
angular.module('BE.seed.service.mapping', []).factory('mapping_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  function ($http, $q, $timeout, user_service) {
    var mapping_factory = {};

    /*
     * Get the data we need to build mapping views.
     *
     * @param import_file_id: integer, number db id for this imported file.
     *
     * @returns object:
     *  {
     *      "status": "success",
     *      "suggested_mappings":{}
     *      "building_columns": []
     *      "building_column_types": {}
     *  }
     */
    mapping_factory.get_column_mapping_suggestions = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.get_column_mapping_suggestions,
            'data': {
              'import_file_id': import_file_id,
              'org_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    mapping_factory.get_raw_columns = function(import_file_id) {
        // timeout here for testing
        var defer = $q.defer();

        $http({
            method: 'POST',
            'url': window.BE.urls.get_raw_column_names,
            'data': {'import_file_id': import_file_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    mapping_factory.get_first_five_rows = function(import_file_id) {
        // timeout here for testing
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.get_first_five_rows,
            'data': {'import_file_id': import_file_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });

        return defer.promise;
    };

    /*
     * Save_mappings
     * Save the mapping between user input data, and our BS attributes.
     */
    mapping_factory.save_mappings = function(import_file_id, mappings) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.save_column_mappings,
            'data': {
                'mappings': mappings,
                'import_file_id': import_file_id,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });

        return defer.promise;

    };

    /*
     * Start mapping.
     * kick off task to begin mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.start_mapping = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.start_mapping,
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

    /*
     * remap_buildings
     * kick off task to begin re-mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.remap_buildings = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.remap_buildings,
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

    return mapping_factory;
}]);
