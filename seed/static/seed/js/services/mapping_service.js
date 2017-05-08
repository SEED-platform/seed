/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// mapping services
angular.module('BE.seed.service.mapping', []).factory('mapping_service', [
  '$http',
  'user_service',
  function ($http, user_service) {
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
    mapping_factory.get_column_mapping_suggestions = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/mapping_suggestions/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    mapping_factory.get_raw_columns = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/raw_column_names/').then(function (response) {
        return response.data;
      });
    };

    mapping_factory.get_first_five_rows = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/first_five_rows/').then(function (response) {
        return response.data;
      });
    };

    /*
     * Save_mappings
     * Save the mapping between user input data, and our BS attributes.
     */
    mapping_factory.save_mappings = function (import_file_id, mappings) {
      return $http.post(
          '/api/v2/import_files/' + import_file_id + '/save_column_mappings/',
          {
            mappings: mappings,
            organization_id: user_service.get_organization().id
          }
      ).then(function (response) {
        return response.data;
      });
    };

    /*
     * Start mapping.
     * kick off task to begin mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.start_mapping = function (import_file_id) {
      return $http.post(
          '/api/v2/import_files/' + import_file_id + '/perform_mapping/',
          {
            remap: false,
            mark_as_done: false,
            organization_id: user_service.get_organization().id
          }
      ).then(function (response) {
        return response.data;
      });
    };

    /*
     * remap_buildings
     * kick off task to begin re-mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.remap_buildings = function (import_file_id) {
      return $http.post(
          '/api/v2/import_files/' + import_file_id + '/perform_mapping/',
          {
            remap: true,
            mark_as_done: false,
            organization_id: user_service.get_organization().id
          }
      ).then(function (response) {
        return response.data;
      });
    };

    return mapping_factory;
  }]);
