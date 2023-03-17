/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.main', []).factory('main_service', [
  '$http',
  function ($http) {
    var main_factory = {};

    main_factory.version = function () {
      return $http.get('/api/version/').then(function (response) {
        return response.data;
      });
    };

    return main_factory;
  }]);
