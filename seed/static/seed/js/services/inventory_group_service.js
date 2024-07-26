/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.service.inventory_group', []).factory('inventory_group_service', [
  '$http',
  'user_service',
  'naturalSort',
  function ($http, user_service, naturalSort) {

    var group_factory = {};

    function map_group (group) {
      if (group.member_list.length) {
        group.has_members = true;
      }
      else {
        group.has_members = false;
      }
      group.is_checked_add = false;
      group.is_checked_remove = false;
      return group;
    }

    function map_groups (response) {
      return _.map(response.data.data, map_group).sort(function (a, b) {
        return naturalSort(a.name, b.name);
      });
    }

    /*Passing an inventory type will return all groups & corresponding inv type they're applied to
      Passing inventory type & filter_ids will return all groups, limited to only selected props/taxlots*/
    group_factory.get_groups_for_inventory = function (inventory_type, filter_ids) {
      var params = {
          organization_id: user_service.get_organization().id
        };
        var body = null;
        if (inventory_type === 'properties') {
          params.inventory_type = 'property';
          body = {selected: filter_ids};
        } else if (inventory_type === 'taxlots') {
          params.inventory_type = 'tax_lot';
          body = {selected: filter_ids};
        }
        return $http.post('/api/v3/inventory_groups/filter/', body, {
          params: params
        }).then(map_groups);
    };

    group_factory.get_groups = function (inventory_type) {
      return group_factory.get_groups_for_org(user_service.get_organization().id, inventory_type);
    };

    group_factory.get_groups_for_org = function (organization_id, inventory_type) {
      return $http.get('/api/v3/inventory_groups/', {
        params: {
          organization_id: organization_id,
          inventory_type: inventory_type
        }
      }).then(function (response) {
        var groups = response.data.data.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });
        return groups;
      });
    };

    group_factory.new_group = function (data) {
      return $http.post('/api/v3/inventory_groups/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    group_factory.update_group = function (id, data) {
      if (id === null) {
        Notification.error('This group is protected from modifications');
        return $q.reject();
      }
      return $http.put('/api/v3/inventory_groups/' + id + '/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    group_factory.remove_group = function (id) {
      if (id === null) {
        Notification.error('This group is protected from modifications');
        return $q.reject();
      }
      return $http.delete('/api/v3/inventory_groups/' + id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      });
    };

    group_factory.update_inventory_groups = function (add_group_ids, remove_group_ids, selected, inventory_type) {
      return $http.put('/api/v3/inventory_group_mappings/put/', {
        inventory_ids: selected,
        add_group_ids: add_group_ids,
        remove_group_ids: remove_group_ids,
        inventory_type: inventory_type
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return group_factory;

  }]);
