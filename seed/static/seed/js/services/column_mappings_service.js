/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.column_mappings', []).factory('column_mappings_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var column_mappings_factory = {};

    column_mappings_factory.get_column_mappings = function () {
      return column_mappings_factory.get_column_mappings_for_org(user_service.get_organization().id);
    };

    column_mappings_factory.get_column_mappings_for_org = function (org_id) {
      return $http.get('/api/v2/column_mappings/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return _.map(response.data, function (mapping) {
          if (_.isEmpty(mapping.column_mapped.display_name)) {
            mapping.column_mapped.display_name = mapping.column_mapped.column_name;
          }
          return mapping;
        });
      });
    };

    column_mappings_factory.get_column_mapping_presets_for_org = function (org_id) {
      return $http.get('/api/v2/column_mapping_presets/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.new_column_mapping_preset_for_org = function (org_id, data) {
      return $http.post('/api/v2/column_mapping_presets/', data, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.get_header_suggestions = function (headers) {
      return column_mappings_factory.get_header_suggestions_for_org(user_service.get_organization().id, headers);
    };

    column_mappings_factory.get_header_suggestions_for_org = function (org_id, headers) {
      return $http.post('/api/v2/column_mapping_presets/suggestions/', {
        headers: headers,
      }, {
        params: {
          organization_id: org_id,
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.update_column_mapping_preset = function (org_id, id, data) {
      return $http.put('/api/v2/column_mapping_presets/' + id + '/', data, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.delete_column_mapping_preset = function (org_id, id) {
      return $http.delete('/api/v2/column_mapping_presets/' + id + '/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.delete_column_mapping = function (id) {
      return column_mappings_factory.delete_column_mapping_for_org(user_service.get_organization().id, id);
    };

    column_mappings_factory.delete_column_mapping_for_org = function (org_id, id) {
      return $http.delete('/api/v2/column_mappings/' + id + '/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.delete_all_column_mappings = function () {
      return column_mappings_factory.delete_all_column_mappings_for_org(user_service.get_organization().id);
    };

    column_mappings_factory.delete_all_column_mappings_for_org = function (org_id) {
      return $http.post('/api/v2/column_mappings/delete_all/', {}, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return column_mappings_factory;

  }]);
