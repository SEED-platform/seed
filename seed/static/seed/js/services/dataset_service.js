/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.dataset', []).factory('dataset_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  function ($http, $q, $timeout, user_service) {

    var dataset_factory = {total_datasets_for_user: 0};

    dataset_factory.get_datasets = function () {
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: '/api/v2/datasets/',
        params: {
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        dataset_factory.total_datasets_for_user = (data.datasets !== undefined) ? data.datasets.length : 0;
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;

    };

    dataset_factory.get_dataset = function (dataset_id) {
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: '/api/v2/datasets/' + dataset_id + '/',
        params: {
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;
    };

    dataset_factory.delete_file = function (file_id) {
      var defer = $q.defer();
      $http({
        method: 'DELETE',
        url: window.BE.urls.delete_file,
        data: {
          file_id: file_id,
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;
    };

    dataset_factory.delete_dataset = function (dataset_id) {
      var defer = $q.defer();
      $http({
        method: 'DELETE',
        url: '/api/v2/datasets/' + dataset_id + '/',
        params: {
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;
    };

    dataset_factory.update_dataset = function (dataset) {
      var defer = $q.defer();
      $http({
        method: 'PUT',
        url: '/api/v2/datasets/' + dataset.id + '/',
        data: {
          dataset: dataset.name
        },
        params: {
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;
    };

    dataset_factory.get_import_file = function (import_file_id) {
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: window.BE.urls.get_import_file,
        params: {
          import_file_id: import_file_id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);

      });
      return defer.promise;
    };

    return dataset_factory;
  }]);
