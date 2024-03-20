/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.main', []).factory('main_service', [
  '$http',
  ($http) => {
    const main_factory = {};

    main_factory.version = () => $http.get('/api/version/').then((response) => response.data);

    return main_factory;
  }
]);
