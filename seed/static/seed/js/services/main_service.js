/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.main', []).factory('main_service', [
  '$http',
  '$q',
  function ($http, $q) {
    var main_factory = {};

    main_factory.version = function() {
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: '/api/v2/version'
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return main_factory;
}]);
