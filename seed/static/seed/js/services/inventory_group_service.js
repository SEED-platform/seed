/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.service.inventory_group', []).factory('inventory_group_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  ($http, $q, user_service, naturalSort) => {
    const group_factory = {};

    function map_group(group) {
      if (group.views_list.length) {
        group.has_members = true;
      } else {
        group.has_members = false;
      }
      group.is_checked_add = false;
      group.is_checked_remove = false;
      return group;
    }

    const map_groups = (response) => _.map(response.data.data, map_group).sort((a, b) => naturalSort(a.name, b.name));

    /* Passing an inventory type will return all groups & corresponding inv type they're applied to
      Passing inventory type & filter_ids will return all groups, limited to only selected props/taxlots */
    group_factory.get_groups_for_inventory = (inventory_type, filter_ids) => {
      const params = {
        organization_id: user_service.get_organization().id
      };
      let body = null;
      if (inventory_type === 'properties') {
        params.inventory_type = 'property';
      } else if (inventory_type === 'taxlots') {
        params.inventory_type = 'tax_lot';
      }
      body = { selected: filter_ids };

      return $http.post('/api/v3/inventory_groups/filter/', body, {
        params
      }).then(map_groups);
    };

    group_factory.get_groups = (inventory_type) => group_factory.get_groups_for_org(user_service.get_organization().id, inventory_type);

    group_factory.get_groups_for_org = (organization_id, inventory_type) => $http.get('/api/v3/inventory_groups/', {
      params: {
        organization_id,
        inventory_type
      }
    }).then((response) => {
      const groups = response.data.data.sort((a, b) => naturalSort(a.name, b.name));
      return groups;
    });

    group_factory.get_group = (organization_id, group_id) => $http.get(`/api/v3/inventory_groups/${group_id}/`, {
      params: {
        organization_id
      }
    }).then((response) => {
      const group = response.data.data;
      return group;
    });

    group_factory.new_group = (data) => $http.post('/api/v3/inventory_groups/', data, {
      params: {
        organization_id: user_service.get_organization().id
      }
    }).then((response) => response.data);

    group_factory.update_group = (id, data) => {
      if (id === null) {
        Notification.error('This group is protected from modifications');
        return $q.reject();
      }
      return $http.put(`/api/v3/inventory_groups/${id}/`, data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then((response) => response.data.data);
    };

    group_factory.get_dashboard_info = (id, cycle_id) => $http.get(
      `/api/v3/inventory_groups/${id}/dashboard/`,
      {
        params: {
          organization_id: user_service.get_organization().id,
          cycle_id
        }
      }
    ).then((response) => response.data.data);

    group_factory.remove_group = (id) => {
      if (id === null) {
        Notification.error('This group is protected from modifications');
        return $q.reject();
      }
      return $http.delete(`/api/v3/inventory_groups/${id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      });
    };

    group_factory.update_inventory_groups = (add_group_ids, remove_group_ids, selected, inventory_type) => $http.put('/api/v3/inventory_group_mappings/put/', {
      inventory_ids: selected,
      add_group_ids,
      remove_group_ids,
      inventory_type
    }, {
      params: {
        organization_id: user_service.get_organization().id
      }
    }).then((response) => response.data);

    group_factory.get_meters_for_group = (id) => $http
      .get(
        `/api/v3/inventory_groups/${id}/meters/`,
        {
          params: { organization_id: user_service.get_organization().id }
        }
      ).then((response) => response.data.data);

    group_factory.get_meter_usage = (id, interval) => $http
      .post(
        `/api/v3/inventory_groups/${id}/meter_usage/`,
        {
          interval
        },
        {
          params: { organization_id: user_service.get_organization().id }
        }
      ).then((response) => response.data.data);

    group_factory.create_group_meter = (group_id, meter_info) => $http
      .post(
        `/api/v3/inventory_groups/${group_id}/meters/`,
        {
          ...meter_info
        },
        {
          params: { organization_id: user_service.get_organization().id }
        }
      ).then((response) => response);
    return group_factory;
  }]);
