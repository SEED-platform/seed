/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.system', []).factory('system_service', [
  '$http',
  ($http) => ({
    // Return a list of systems for a given group
    get_systems: (organization_id, group_id) => $http
      .get(`/api/v3/inventory_groups/${group_id}/systems/`, {
        params: { organization_id }
      }).then(({ data }) => data),

    get_systems_by_type: (organization_id, group_id) => $http
      .get(`/api/v3/inventory_groups/${group_id}/systems/systems_by_type`, {
        params: { organization_id }
      }).then((data) => data.data),

    remove_system: (organization_id, group_id, system_id) => $http
      .delete(`/api/v3/inventory_groups/${group_id}/systems/${system_id}`, {
        params: { organization_id }
      }).then(({ data }) => data),

    // Create a system for a given group
    create_system: (organization_id, group_id, data) => $http
      .post(
        `/api/v3/inventory_groups/${group_id}/systems/`,
        data,
        { params: { organization_id } }
      ).then(({ data }) => data),

    update_system: (organization_id, group_id, system) => $http
      .put(
        `/api/v3/inventory_groups/${group_id}/systems/${system.id}/`,
        system,
        { params: { organization_id } }
      ).then(({ data }) => data),

    // Create a service for a given system
    create_service: (organization_id, group_id, system_id, data) => $http
      .post(
        `/api/v3/inventory_groups/${group_id}/systems/${system_id}/services/`,
        data,
        { params: { organization_id } }
      ).then(({ data }) => data)
  })
]);
