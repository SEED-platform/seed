/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.columns', []).factory('columns_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const columns_service = {};

    columns_service.update_column = (column_id, data) => columns_service.update_column_for_org(user_service.get_organization().id, column_id, data);

    columns_service.create_column_for_org = (org_id, data) => $http
      .post('/api/v3/columns/', {
        organization_id: org_id,
        ...data
      })
      .then((response) => response.data);

    columns_service.update_column_for_org = (org_id, column_id, data) => $http
      .put(`/api/v3/columns/${column_id}/`, data, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    columns_service.rename_column = (column_id, column_name, overwrite_preference) => columns_service.rename_column_for_org(user_service.get_organization().id, column_id, column_name, overwrite_preference);

    columns_service.rename_column_for_org = (org_id, column_id, column_name, overwrite_preference) => $http
      .post(`/api/v3/columns/${column_id}/rename/`, {
        organization_id: org_id,
        new_column_name: column_name,
        overwrite: overwrite_preference
      })
      .then((response) => response)
      .catch((error_response) => ({
        data: {
          success: false,
          message: `Unsuccessful: ${error_response.data.message}`
        }
      }));

    columns_service.delete_column = (column_id) => columns_service.delete_column_for_org(user_service.get_organization().id, column_id);

    columns_service.delete_column_for_org = (org_id, column_id) => $http.delete(`/api/v3/columns/${column_id}/`, {
      params: { organization_id: org_id }
    });

    return columns_service;
  }
]);
