/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.column_mappings', []).factory('column_mappings_service', [
  '$http',
  // 'user_service',
  function ($http/*, user_service*/) {

    var column_mappings_factory = {};

    // unused 6.15.17 commented out for code cov dbressan
    // column_mappings_factory.get_column_mappings = function () {
    //   return column_mappings_factory.get_column_mappings_for_org(user_service.get_organization().id);
    // };

    // column_mappings_factory.get_column_mappings_for_org = function (org_id) {
    //   return $http.get('/api/v2/column_mappings/', {
    //     params: {
    //       organization_id: org_id
    //     }
    //   }).then(function (response) {
    //     return response.data;
    //   });
    // };

    // unused 6.15.17 commented out for code cov dbressan
    // column_mappings_factory.delete_all_column_mappings = function () {
    //   return column_mappings_factory.delete_all_column_mappings_for_org(user_service.get_organization().id);
    // };

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
