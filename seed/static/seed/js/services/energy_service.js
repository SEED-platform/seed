angular.module('BE.seed.service.energy', [])
  .factory('energy_service', [
    '$http',
    function ($http) {
      var energy_factory = {};

      energy_factory.get_meters = function (property_view_id, organization_id, interval) {
        return $http.post('/api/v2/meters/property_meters/', {
          property_view_id: property_view_id,
        }).then(function (response) {
          return response.data;
        });
      };

      energy_factory.property_energy_usage = function (property_view_id, organization_id, interval, excluded_meter_ids = []) {
        return $http.post('/api/v2/meters/property_energy_usage/', {
          property_view_id: property_view_id,
          organization_id: organization_id,
          interval: interval,
          excluded_meter_ids: excluded_meter_ids,
        }).then(function (response) {
          return response.data;
        });
      };

      return energy_factory;
    }
  ]);
