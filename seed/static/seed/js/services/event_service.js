/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.event', []).factory('event_service', [
  '$http',
  ($http) => {
    const event_factory = {};

    event_factory.get_events = (org_id, inventory_type, property_pk) => $http
      .get(`/api/v3/${inventory_type}/${property_pk}/events/`, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    return event_factory;
  }
]);
