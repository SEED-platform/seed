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

      bluesky_service.get_properties = function() {
          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_properties,
              params: {
                  organization_id: user_service.get_organization().id
              }
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      }

      bluesky_service.get_taxlots = function() {
          var defer = $q.defer();
          $http({
              method: 'GET',
              url: window.BE.urls.get_taxlots,
              params: {
                  organization_id: user_service.get_organization().id
              }
          }).success(function(data, status, headers, config) {
              defer.resolve(data);
          }).error(function(data, status, headers, config) {
              defer.reject(data, status);
          });
          return defer.promise;
      }

      return bluesky_service;
}]);
