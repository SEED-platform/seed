/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.column_mappings', []).factory('column_mappings_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const column_mappings_factory = {};

    column_mappings_factory.get_column_mapping_profiles_for_org = (org_id, filter_profile_types) => {
      let data;
      const params = {
        organization_id: org_id
      };
      if (filter_profile_types != null) {
        data = {
          profile_type: filter_profile_types
        };
      }
      return $http
        .post('/api/v3/column_mapping_profiles/filter/', data, {
          params
        })
        .then((response) => response.data);
    };

    column_mappings_factory.new_column_mapping_profile_for_org = (org_id, data) => $http
      .post('/api/v3/column_mapping_profiles/', data, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    column_mappings_factory.get_header_suggestions = (headers) => column_mappings_factory.get_header_suggestions_for_org(user_service.get_organization().id, headers);

    column_mappings_factory.get_header_suggestions_for_org = (org_id, headers) => $http
      .post(
        '/api/v3/column_mapping_profiles/suggestions/',
        {
          headers
        },
        {
          params: {
            organization_id: org_id
          }
        }
      )
      .then((response) => response.data);

    column_mappings_factory.update_column_mapping_profile = (org_id, id, data) => $http
      .put(`/api/v3/column_mapping_profiles/${id}/`, data, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    column_mappings_factory.delete_column_mapping_profile = (org_id, id) => $http
      .delete(`/api/v3/column_mapping_profiles/${id}/`, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    /**
     * return column mapping profile in CSV format.
     * @param  {int} org_id the id of the organization, not needed, but useful to still pass around
     * @param  {int} profile_id the profile id of the column mapping to be exported
     */
    column_mappings_factory.export_mapping_profile = (org_id, profile_id) => $http.get(`/api/v3/column_mapping_profiles/${profile_id}/csv/?organization_id=${org_id}`).then((response) => response.data);

    return column_mappings_factory;
  }
]);
