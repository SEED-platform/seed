/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.main', []).factory('main_service', [
  '$http',
  function ($http) {
    var main_factory = {};

    main_factory.version = function () {
      return $http.get('/api/v2/version').then(function (response) {
        return response.data;
      });
    };

    return main_factory;
  }]);
