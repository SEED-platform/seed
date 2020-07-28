angular.module('BE.seed.service.meters', [])
  .factory('meters_service', [
    '$http',
    function ($http) {
      var meters_factory = {};

      meters_factory.valid_energy_types_units = function () {
        return $http.get('/api/v3/meters/valid_types_units/').then(function (response) {
          return response.data;
        });
      };

      return meters_factory;
    }
  ]);
