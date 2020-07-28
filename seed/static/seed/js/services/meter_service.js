angular.module('BE.seed.service.meter', [])
  .factory('meter_service', [
    '$http',
    function ($http) {
      var meter_factory = {};

      meter_factory.get_meters = function (property_view_id, organization_id) {
        return $http.get(
          '/api/v3/properties/' + property_view_id + '/meters/',
          { params: { organization_id } }
        ).then(function (response) {
          return response.data;
        });
      };

      meter_factory.property_meter_usage = function (property_view_id, organization_id, interval, excluded_meter_ids) {
        if (_.isUndefined(excluded_meter_ids)) excluded_meter_ids = [];
        return $http.post(
          '/api/v3/properties/' + property_view_id + '/meter_usage/?organization_id=' + organization_id,
          {
            interval: interval,
            excluded_meter_ids: excluded_meter_ids
          }
        ).then(function (response) {
          return response.data;
        });
      };

      return meter_factory;
    }
  ]);
