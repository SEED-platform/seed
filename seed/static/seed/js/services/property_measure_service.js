/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.property_measure', []).factory('property_measure_service', [
  '$http',
  ($http) => {
    const property_measure_factory = {};

    property_measure_factory.delete_property_measure = (organization_id, property_view_id, scenario_id, property_measure_id) => $http({
      url: `/api/v3/properties/${property_view_id}/scenarios/${scenario_id}/measures/${property_measure_id}?organization_id=${organization_id}`,
      method: 'DELETE'
    }).then((response) => response.data);

    return property_measure_factory;
  }
]);
