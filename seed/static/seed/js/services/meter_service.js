/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.meter', []).factory('meter_service', [
  '$http',
  ($http) => {
    const meter_factory = {};

    meter_factory.get_meters = (property_view_id, organization_id) => $http.get(`/api/v3/properties/${property_view_id}/meters/`, { params: { organization_id } }).then((response) => response.data);

    meter_factory.delete_meter = (property_view_id, meter_id) => $http.delete(`/api/v3/properties/${property_view_id}/meters/${meter_id}`).then((response) => response.data);

    meter_factory.property_meter_usage = (property_view_id, organization_id, interval, excluded_meter_ids) => {
      if (_.isUndefined(excluded_meter_ids)) excluded_meter_ids = [];
      return $http
        .post(`/api/v3/properties/${property_view_id}/meter_usage/?organization_id=${organization_id}`, {
          interval,
          excluded_meter_ids
        })
        .then((response) => response.data);
    };

    return meter_factory;
  }
]);
