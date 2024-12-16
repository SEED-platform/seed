/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.service', []).factory('service_service', [
  '$http',
  ($http) => ({
    remove_service: (organization_id, group_id, system_id, service_id) => $http
      .delete(`/api/v3/inventory_groups/${group_id}/systems/${system_id}/services/${service_id}/`, {
        params: { organization_id }
      }).then(({ data }) => data),

    create_service: (organization_id, group_id, system_id, service) => $http
      .post(
        `/api/v3/inventory_groups/${group_id}/systems/${system_id}/services/`,
        service,
        { params: { organization_id } }
      ).then(({ data }) => data),

    update_service: (organization_id, group_id, system_id, service) => $http
      .put(
        `/api/v3/inventory_groups/${group_id}/systems/${system_id}/services/${service.id}/`,
        service,
        { params: { organization_id } }
      ).then(({ data }) => data)
  })
]);
