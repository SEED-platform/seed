angular.module('BE.seed.service.energy', [])
  .factory('energy_service', [
    '$http',
    function ($http) {
      var energy_factory = {};

      energy_factory.property_energy_usage = function (property_view_id, organization_id, interval) {
        return $http.post('/api/v2/meters/property_energy_usage/', {
          property_view_id: property_view_id,
          organization_id: organization_id,
          interval: interval,
        }).then(function (response) {
          return response.data;
        });
      };

      return energy_factory;
    }
  ]);
