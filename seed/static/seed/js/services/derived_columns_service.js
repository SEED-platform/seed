/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.derived_columns', []).factory('derived_columns_service', [
  '$http',
  function ($http) {

    const derived_columns_factory = {};

    derived_columns_factory.get_derived_columns = function(organization_id, inventory_type) {
      return $http({
        url: '/api/v3/derived_columns/',
        method: 'GET',
        params: { organization_id, inventory_type }
      }).then(function (response) {
        return response.data;
      });
    };

    derived_columns_factory.get_derived_column = function(organization_id, derived_column_id) {
      return $http({
        url: `/api/v3/derived_columns/${derived_column_id}`,
        method: 'GET',
        params: { organization_id }
      }).then(function (response) {
        return response.data;
      });
    };

    derived_columns_factory.create_derived_column = function(organization_id, { name, expression, inventory_type, parameters }) {
      return $http({
        url: `/api/v3/derived_columns/`,
        method: 'POST',
        params: { organization_id },
        data: { name, expression, inventory_type, parameters }
      }).then(function (response) {
        return response.data;
      });
    }

    derived_columns_factory.update_derived_column = function(organization_id, derived_column_id, { name, expression, inventory_type, parameters }) {
      return $http({
        url: `/api/v3/derived_columns/${derived_column_id}/`,
        method: 'PUT',
        params: { organization_id },
        data: { name, expression, inventory_type, parameters }
      }).then(function (response) {
        return response.data;
      });
    }

    derived_columns_factory.delete_derived_column = function(organization_id, derived_column_id) {
      return $http({
        url: `/api/v3/derived_columns/${derived_column_id}/`,
        method: 'DELETE',
        params: { organization_id },
      }).then(function (response) {
        return response.data;
      });
    }

    derived_columns_factory.evaluate = function(organization_id, derived_column_id, cycle_id, inventory_ids) {
      return $http({
        url: `/api/v3/derived_columns/${derived_column_id}/evaluate/`,
        method: 'GET',
        params: { organization_id, cycle_id, inventory_ids: inventory_ids.join(',') },
      }).then(function (response) {
        return response.data;
      });
    }
    return derived_columns_factory;
  }]);
