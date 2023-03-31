/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.mapping', []).factory('mapping_service', [
  '$http',
  'user_service',
  function ($http, user_service) {
    var mapping_factory = {};

    /**
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
      return $http.get('/api/v3/import_files/' + import_file_id + '/mapping_suggestions/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    mapping_factory.get_raw_columns = function (import_file_id) {
      return $http.get('/api/v3/import_files/' + import_file_id + '/raw_column_names/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    mapping_factory.get_first_five_rows = function (import_file_id) {
      return $http.get('/api/v3/import_files/' + import_file_id + '/first_five_rows/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * Save_mappings
     * Save the mapping between user input data, and our BS attributes.
     */
    mapping_factory.save_mappings = function (import_file_id, mappings) {
      const organization_id = user_service.get_organization().id;
      return $http.post('/api/v3/organizations/' + organization_id + '/column_mappings/', {
        mappings
      }, {
        params: { import_file_id }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * Start mapping.
     * kick off task to begin mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.start_mapping = function (import_file_id) {
      return $http.post('/api/v3/import_files/' + import_file_id + '/map/', {
        remap: false,
        mark_as_done: false
      }, {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * remap_buildings
     * kick off task to begin re-mapping on the backend.
     * @param import_file_id: int, represents file import id.
     */
    mapping_factory.remap_buildings = function (import_file_id) {
      return $http.post('/api/v3/import_files/' + import_file_id + '/map/', {
        remap: true,
        mark_as_done: false
      }, {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      });
    };

    return mapping_factory;
  }]);
