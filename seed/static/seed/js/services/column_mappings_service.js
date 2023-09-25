/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.column_mappings', []).factory('column_mappings_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var column_mappings_factory = {};

    column_mappings_factory.get_column_mapping_profiles_for_org = function (org_id, filter_profile_types) {
      var data;
      var params = {
        organization_id: org_id
      };
      if (filter_profile_types != null) {
        data = {
          profile_type: filter_profile_types
        };
      }
      return $http.post('/api/v3/column_mapping_profiles/filter/', data, {
        params: params
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.new_column_mapping_profile_for_org = function (org_id, data) {
      return $http.post('/api/v3/column_mapping_profiles/', data, {
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
      return $http.post('/api/v3/column_mapping_profiles/suggestions/', {
        headers: headers
      }, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.update_column_mapping_profile = function (org_id, id, data) {
      return $http.put('/api/v3/column_mapping_profiles/' + id + '/', data, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    column_mappings_factory.delete_column_mapping_profile = function (org_id, id) {
      return $http.delete('/api/v3/column_mapping_profiles/' + id + '/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * return column mapping profile in CSV format.
     * @param  {int} org_id the id of the organization, not needed, but useful to still pass around
     * @param  {int} profile_id the profile id of the column mapping to be exported
     */
     column_mappings_factory.export_mapping_profile = function (org_id, profile_id) {
      return $http.get('/api/v3/column_mapping_profiles/' + profile_id + '/csv/?organization_id=' + org_id).then(function (response) {
        return response.data;
      });
    };

    return column_mappings_factory;

  }]);
