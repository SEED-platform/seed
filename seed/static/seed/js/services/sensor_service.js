angular.module('BE.seed.service.sensor', [])
  .factory('sensor_service', [
    '$http',
    function ($http) {
      var sensor_factory = {};

      sensor_factory.get_sensors = function (property_view_id, organization_id) {
        return $http.get(
          '/api/v3/properties/' + property_view_id + '/sensors/',
          { params: { organization_id } }
        ).then(function (response) {
          return response.data;
        });
      };

      return sensor_factory;
    }
  ]);
