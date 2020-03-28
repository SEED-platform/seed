/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.dataset', []).factory('dataset_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var dataset_service = {total_datasets_for_user: 0};

    dataset_service.get_datasets_count = function () {
      return $http.get('/api/v2/datasets/count/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        dataset_service.total_datasets_for_user = response.data.datasets_count;
        return response.data;
      });
    };

    dataset_service.get_datasets = function () {
      return $http.get('/api/v2/datasets/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        dataset_service.total_datasets_for_user = _.has(response.data.datasets, 'length') ? response.data.datasets.length : 0;
        return response.data;
      });
    };

    dataset_service.get_dataset = function (dataset_id) {
      return $http.get('/api/v2/datasets/' + dataset_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.delete_file = function (file_id) {
      return $http.delete('/api/v2/import_files/' + file_id + '/', {
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
      return $http.delete('/api/v2/datasets/' + dataset_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    dataset_service.update_dataset = function (dataset) {
      return $http.put('/api/v2/datasets/' + dataset.id + '/', {
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
      return $http.get('/api/v2/import_files/' + import_file_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return dataset_service;
  }]);
