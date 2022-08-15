/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.filter_groups', []).factory('filter_groups_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  function ($http, $q, user_service, naturalSort) {

    var filter_groups_factory = {};

    filter_groups_factory.get_filter_groups = function () {
      return $http.get('/api/v3/filter_groups/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        var filter_groups = response.data.data.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });

        return filter_groups;
      });
    };

    filter_groups_factory.get_last_filter_group = function (key) {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('filter_groups.' + key)) || {})[organization_id];
    };

    filter_groups_factory.save_last_filter_group = function (pk, key) {
      var organization_id = user_service.get_organization().id,
        filter_groups = JSON.parse(localStorage.getItem('filter_groups.' + key)) || {};
        filter_groups[organization_id] = _.toInteger(pk);
      localStorage.setItem('filter_groups.' + key, JSON.stringify(filter_groups));
    };

    filter_groups_factory.get_filter_group = function (id) {
      return $http.get('/api/v3/filter_groups/' + id, {
        params: {
          organization_id: user_service.get_organization().id,
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    // filter_groups_factory.new_filter_group_for_org = function (org_id, data) {
    //   return $http.post('/api/v3/filter_groups/', data, {
    //     params: {
    //       organization_id: org_id
    //     }
    //   }).then(function (response) {
    //     return response.data;
    //   });
    // };

    // filter_groups_factory.get_header_suggestions = function (headers) {
    //   return filter_groups_factory.get_header_suggestions_for_org(user_service.get_organization().id, headers);
    // };

    // filter_groups_factory.get_header_suggestions_for_org = function (org_id, headers) {
    //   return $http.post('/api/v3/filter_groups/suggestions/', {
    //     headers: headers
    //   }, {
    //     params: {
    //       organization_id: org_id
    //     }
    //   }).then(function (response) {
    //     return response.data;
    //   });
    // };

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
