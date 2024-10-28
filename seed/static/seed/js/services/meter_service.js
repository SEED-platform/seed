/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.meter', []).factory('meter_service', [
  '$http',
  ($http) => {
    const meter_factory = {};

    meter_factory.get_meters = (property_view_id, organization_id) => $http.get(`/api/v3/properties/${property_view_id}/meters/`, { params: { organization_id } }).then((response) => response.data);

    meter_factory.delete_meter = (organization_id, property_view_id, meter_id) => $http
      .delete(`/api/v3/properties/${property_view_id}/meters/${meter_id}/?organization_id=${organization_id}`)
      .then((response) => response)
      .catch((response) => response);

    meter_factory.update_meter_connection = (organization_id, meter_id, meter_config, property_view_id = null, group_id = null) => {
      if (property_view_id) {
        return meter_factory.update_property_meter_connection(organization_id, meter_id, meter_config, property_view_id);
      } if (group_id) {
        return meter_factory.update_group_meter_connection(organization_id, meter_id, meter_config, group_id);
      }
    };

    meter_factory.update_property_meter_connection = (organization_id, meter_id, meter_config, property_view_id) => $http
      .put(
        `/api/v3/properties/${property_view_id}/meters/${meter_id}/update_connection/?organization_id=${organization_id}`,
        { meter_config }
      )
      .then((response) => response)
      .catch((response) => response);

    meter_factory.update_group_meter_connection = (organization_id, meter_id, meter_config, group_id) => $http
      .put(
        `/api/v3/inventory_groups/${group_id}/meters/${meter_id}/update_connection/?organization_id=${organization_id}`,
        { meter_config }
      )
      .then((response) => response)
      .catch((response) => response);

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
