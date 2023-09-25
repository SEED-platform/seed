/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.filter_groups', []).factory('filter_groups_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  function ($http, $q, user_service, naturalSort) {

    var filter_groups_factory = {};

    filter_groups_factory.get_filter_groups = function (inventory_type, organization_id = user_service.get_organization().id) {
      return $http.get('/api/v3/filter_groups/', {
        params: {
          organization_id,
          inventory_type,
        }
      }).then(function (response) {
        var filter_groups = response.data.data.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });

        return filter_groups;
      });
    };

    filter_groups_factory.get_last_filter_group = function (inventory_type) {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('filter_groups.' + inventory_type)) || {})[organization_id];
    };

    filter_groups_factory.save_last_filter_group = function (id, inventory_type) {
      var organization_id = user_service.get_organization().id,
        filter_groups = JSON.parse(localStorage.getItem('filter_groups.' + inventory_type)) || {};
      if (id === -1) {
        delete filter_groups[organization_id];
      } else {
        filter_groups[organization_id] = id;
      }
      localStorage.setItem('filter_groups.' + inventory_type, JSON.stringify(filter_groups));
    };

    filter_groups_factory.get_filter_group = function (id) {
      return $http.get('/api/v3/filter_groups/' + id + '/', {
        params: {
          organization_id: user_service.get_organization().id,
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    filter_groups_factory.new_filter_group = function (data) {
      return $http.post('/api/v3/filter_groups/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    filter_groups_factory.update_filter_group = function (id, data) {
      if (id === null) {
        Notification.error('This filter group is protected from modifications');
        return $q.reject();
      }
      return $http.put('/api/v3/filter_groups/' + id + '/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    filter_groups_factory.remove_filter_group = function (id) {
      if (id === null) {
        Notification.error('This filter group is protected from modifications');
        return $q.reject();
      }
      return $http.delete('/api/v3/filter_groups/' + id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return filter_groups_factory;

  }]);
