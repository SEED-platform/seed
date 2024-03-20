/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.data_view', []).factory('data_view_service', [
  '$http',
  '$log',
  'user_service',
  ($http, $log, user_service) => {
    const get_data_view = (data_view_id) => {
      if (_.isNil(data_view_id)) {
        $log.error('#data_view_service.get_data_view(): data_view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .get(`/api/v3/data_views/${data_view_id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data.data_view)
        .catch((response) => response.data);
    };

    const get_data_views = () => $http
      .get('/api/v3/data_views/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data_views)
      .catch((response) => response.data);

    const create_data_view = (name, filter_groups, cycles, data_aggregations) => $http
      .post(
        '/api/v3/data_views/',
        {
          name,
          filter_groups,
          cycles,
          parameters: data_aggregations
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data)
      .catch((response) => response.data);

    const update_data_view = (id, name, filter_groups, cycles, data_aggregations) => $http
      .put(
        `/api/v3/data_views/${id}/`,
        {
          name,
          filter_groups,
          cycles,
          parameters: data_aggregations
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data)
      .catch((response) => response.data);

    const delete_data_view = (data_view_id) => {
      if (_.isNil(data_view_id)) {
        $log.error('#data_view_service.get_data_view(): data_view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .delete(`/api/v3/data_views/${data_view_id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const evaluate_data_view = (data_view_id, columns) => $http
      .put(
        `/api/v3/data_views/${data_view_id}/evaluate/`,
        {
          columns
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data.data)
      .catch((response) => response.data);

    const data_view_factory = {
      create_data_view,
      delete_data_view,
      evaluate_data_view,
      get_data_view,
      get_data_views,
      update_data_view
    };

    return data_view_factory;
  }
]);
