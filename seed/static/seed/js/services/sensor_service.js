angular.module('BE.seed.service.sensor', [])
  .factory('sensor_service', [
    '$http',
    function ($http) {
      var sensor_factory = {};

      sensor_factory.get_data_loggers = function (property_view_id, organization_id) {
        return $http.get(
          '/api/v3/properties/' + property_view_id + '/data_loggers/',
          { params: { organization_id } }
        ).then(function (response) {
          return response.data;
        });
      };

      sensor_factory.get_sensors = function (property_view_id, organization_id) {
        return $http.get(
          '/api/v3/properties/' + property_view_id + '/sensors/',
          { params: { organization_id } }
        ).then(function (response) {
          return response.data;
        });
      };

      sensor_factory.property_sensor_usage = function (property_view_id, organization_id, interval, excluded_sensor_ids) {
        if (_.isUndefined(excluded_sensor_ids)) excluded_sensor_ids = [];
        return $http.post(
          '/api/v3/properties/' + property_view_id + '/sensor_usage/?organization_id=' + organization_id,
          {
            interval: interval,
            excluded_sensor_ids: excluded_sensor_ids
          }
        ).then(function (response) {
          return response.data;
        });
      };

      return sensor_factory;
    }
  ]);
