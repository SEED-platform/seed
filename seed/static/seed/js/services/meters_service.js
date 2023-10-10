/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.meters', []).factory('meters_service', [
  '$http',
  ($http) => {
    const meters_factory = {};

    meters_factory.valid_energy_types_units = () => $http.get('/api/v3/properties/valid_meter_types_and_units/').then((response) => response.data);

    return meters_factory;
  }
]);
