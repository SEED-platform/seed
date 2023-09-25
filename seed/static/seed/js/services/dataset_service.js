/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.dataset', []).factory('dataset_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var dataset_service = {total_datasets_for_user: 0};

    dataset_service.get_datasets_count = function () {
      return $http.get('/api/v3/datasets/count/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        dataset_service.total_datasets_for_user = response.data.datasets_count;
        return response.data;
      });
    };

    dataset_service.get_datasets = function () {
      return $http.get('/api/v3/datasets/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        dataset_service.total_datasets_for_user = _.has(response.data.datasets, 'length') ? response.data.datasets.length : 0;
        return response.data;
      });
    };

    dataset_service.get_dataset = function (dataset_id) {
      return $http.get('/api/v3/datasets/' + dataset_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.delete_file = function (file_id) {
      return $http.delete('/api/v3/import_files/' + file_id + '/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.delete_dataset = function (dataset_id) {
      return $http.delete('/api/v3/datasets/' + dataset_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.update_dataset = function (dataset) {
      return $http.put('/api/v3/datasets/' + dataset.id + '/', {
        dataset: dataset.name
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.get_import_file = function (import_file_id) {
      return $http.get('/api/v3/import_files/' + import_file_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.check_meters_tab_exists = function (file_id) {
      return $http.get('/api/v3/import_files/' + file_id + '/check_meters_tab_exists', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.reuse_inventory_file_for_meters = function (file_id) {
      return $http.post('/api/v3/import_files/reuse_inventory_file_for_meters/', {
        import_file_id: file_id,
        organization_id: user_service.get_organization().id
      }).then(function (response) {
        return response.data;
      });
    };

    return dataset_service;
  }]);
