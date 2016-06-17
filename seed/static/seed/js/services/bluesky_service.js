/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.bluesky_service', [])
.factory('bluesky_service', [
  '$http',
  '$q',
  'urls',
  'user_service',
  function ($http, $q, urls, user_service) {
      var bluesky_service = {};

      bluesky_service.get_properties = function(page, per_page, cycle) {
          var params = {
              organization_id: user_service.get_organization().id,
              page: page,
              per_page: per_page || 999999999
          };

          if (cycle) {
              params.cycle = cycle.pk;
          }

          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_properties,
              params: params
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      };

      bluesky_service.get_taxlots = function(page, per_page, cycle) {
          var params = {
              organization_id: user_service.get_organization().id,
              page: page,
              per_page: per_page
          };

          if (cycle) {
              params.cycle = cycle.pk;
          }

          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_taxlots,
              params: params
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      };

      bluesky_service.get_cycles = function() {
          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_cycles,
              params: {
                  organization_id: user_service.get_organization().id
              }
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      };

      bluesky_service.get_property_columns = function() {
          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_property_columns,
              params: {
                  organization_id: user_service.get_organization().id
              }
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      };

      bluesky_service.get_taxlot_columns = function() {
          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_taxlot_columns,
              params: {
                  organization_id: user_service.get_organization().id
              }
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      };
      return bluesky_service;
}]);
