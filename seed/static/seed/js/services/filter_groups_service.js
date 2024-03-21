/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.filter_groups', []).factory('filter_groups_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  ($http, $q, user_service, naturalSort) => {
    const filter_groups_factory = {};

    filter_groups_factory.get_filter_groups = (inventory_type, organization_id = user_service.get_organization().id) => $http
      .get('/api/v3/filter_groups/', {
        params: {
          organization_id,
          inventory_type
        }
      })
      .then((response) => {
        const filter_groups = response.data.data.sort((a, b) => naturalSort(a.name, b.name));

        return filter_groups;
      });

    filter_groups_factory.get_last_filter_group = (inventory_type) => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem(`filter_groups.${inventory_type}`)) || {})[organization_id];
    };

    filter_groups_factory.save_last_filter_group = (id, inventory_type) => {
      const organization_id = user_service.get_organization().id;
      const filter_groups = JSON.parse(localStorage.getItem(`filter_groups.${inventory_type}`)) || {};
      if (id === -1) {
        delete filter_groups[organization_id];
      } else {
        filter_groups[organization_id] = id;
      }
      localStorage.setItem(`filter_groups.${inventory_type}`, JSON.stringify(filter_groups));
    };

    filter_groups_factory.get_filter_group = (id) => $http
      .get(`/api/v3/filter_groups/${id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    filter_groups_factory.new_filter_group = (data) => $http
      .post('/api/v3/filter_groups/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    filter_groups_factory.update_filter_group = (id, data) => {
      if (id === null) {
        Notification.error('This filter group is protected from modifications');
        return $q.reject();
      }
      return $http
        .put(`/api/v3/filter_groups/${id}/`, data, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data.data);
    };

    filter_groups_factory.remove_filter_group = (id) => {
      if (id === null) {
        Notification.error('This filter group is protected from modifications');
        return $q.reject();
      }
      return $http
        .delete(`/api/v3/filter_groups/${id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data);
    };

    return filter_groups_factory;
  }
]);
