/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.columns', []).factory('columns_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var columns_service = {};

    columns_service.patch_column = function (column_id, data) {
      return columns_service.patch_column_for_org(user_service.get_organization().id, column_id, data);
    };

    columns_service.patch_column_for_org = function (org_id, column_id, data) {
      return $http.patch('/api/v2/columns/' + column_id + '/', data, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    columns_service.rename_column = function (column_id, column_name, overwrite_preference) {
      return $http.post('/api/v2/columns/' + column_id + '/rename/', {
        organization_id: user_service.get_organization().id,
        new_column_name: column_name,
        overwrite: overwrite_preference
      }).then(function (response) {
        return response;
      }).catch(function (error_response) {
        return {
          data: {
            success: false,
            message: 'Unsuccessful: ' + error_response.data.message
          }
        };
      });
    };

    return columns_service;

  }]);
