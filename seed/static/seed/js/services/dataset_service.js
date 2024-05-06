/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.dataset', []).factory('dataset_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const dataset_service = { total_datasets_for_user: 0 };

    dataset_service.get_datasets_count = () => $http
      .get('/api/v3/datasets/count/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => {
        dataset_service.total_datasets_for_user = response.data.datasets_count;
        return response.data;
      });

    dataset_service.get_datasets = () => $http
      .get('/api/v3/datasets/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => {
        dataset_service.total_datasets_for_user = _.has(response.data.datasets, 'length') ? response.data.datasets.length : 0;
        return response.data;
      });

    dataset_service.get_dataset = (dataset_id) => $http
      .get(`/api/v3/datasets/${dataset_id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    dataset_service.delete_file = (file_id) => $http
      .delete(`/api/v3/import_files/${file_id}/`, {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    dataset_service.delete_dataset = (dataset_id) => $http
      .delete(`/api/v3/datasets/${dataset_id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    dataset_service.update_dataset = (dataset) => $http
      .put(
        `/api/v3/datasets/${dataset.id}/`,
        {
          dataset: dataset.name
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    dataset_service.get_import_file = (import_file_id) => $http
      .get(`/api/v3/import_files/${import_file_id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    dataset_service.check_meters_tab_exists = (file_id) => $http
      .get(`/api/v3/import_files/${file_id}/check_meters_tab_exists`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    dataset_service.reuse_inventory_file_for_meters = (file_id) => $http
      .post('/api/v3/import_files/reuse_inventory_file_for_meters/', {
        import_file_id: file_id,
        organization_id: user_service.get_organization().id
      })
      .then((response) => response.data);

    dataset_service.match_merge_inventory = (cycle_id) =>
      $http
      .post('/api/v3/import_files/match_merge_inventory/', {
        organization_id: user_service.get_organization().id,
        cycle_id: cycle_id
      }).then((response) => {
        console.log('dataset service', response.data)
        return response.data
      })


    return dataset_service;
  }
]);
