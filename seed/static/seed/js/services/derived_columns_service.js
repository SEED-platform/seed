/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.derived_columns', []).factory('derived_columns_service', [
  '$http',
  function ($http) {

    const derived_columns_factory = {};

    derived_columns_factory.get_derived_columns = function (organization_id, inventory_type) {
      return $http({
        url: '/api/v3/derived_columns/',
        method: 'GET',
        params: { organization_id, inventory_type }
      }).then(function (response) {
        return response.data;
      });
    };

    return derived_columns_factory;
  }]);
