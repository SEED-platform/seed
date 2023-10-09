/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.derived_columns', []).factory('derived_columns_service', [
  '$http',
  function ($http) {
    const derived_columns_factory = {};

    derived_columns_factory.get_derived_columns = (organization_id, inventory_type) =>
      $http({
        url: '/api/v3/derived_columns/',
        method: 'GET',
        params: { organization_id, inventory_type }
      }).then((response) => response.data);

    derived_columns_factory.get_derived_column = (organization_id, derived_column_id) =>
      $http({
        url: `/api/v3/derived_columns/${derived_column_id}`,
        method: 'GET',
        params: { organization_id }
      }).then((response) => response.data);

    derived_columns_factory.create_derived_column = (organization_id, { name, expression, inventory_type, parameters }) =>
      $http({
        url: '/api/v3/derived_columns/',
        method: 'POST',
        params: { organization_id },
        data: {
          name,
          expression,
          inventory_type,
          parameters
        }
      }).then((response) => response.data);

    derived_columns_factory.update_derived_column = (organization_id, derived_column_id, { name, expression, inventory_type, parameters }) =>
      $http({
        url: `/api/v3/derived_columns/${derived_column_id}/`,
        method: 'PUT',
        params: { organization_id },
        data: {
          name,
          expression,
          inventory_type,
          parameters
        }
      }).then((response) => response.data);

    derived_columns_factory.delete_derived_column = (organization_id, derived_column_id) =>
      $http({
        url: `/api/v3/derived_columns/${derived_column_id}/`,
        method: 'DELETE',
        params: { organization_id }
      }).then((response) => response.data);

    derived_columns_factory.evaluate = (organization_id, derived_column_id, cycle_id, inventory_ids) =>
      $http({
        url: `/api/v3/derived_columns/${derived_column_id}/evaluate/`,
        method: 'GET',
        params: { organization_id, cycle_id, inventory_ids: inventory_ids.join(',') }
      }).then((response) => response.data);
    return derived_columns_factory;
  }
]);
