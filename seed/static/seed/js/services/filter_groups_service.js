/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.filter_groups', []).factory('filter_groups_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var filter_groups_factory = {};

    filter_groups_factory.get_filter_groups = function () {
      return filter_groups_factory.get_filter_groups_for_org(user_service.get_organization().id);
    };

    filter_groups_factory.get_filter_groups_for_org = function (org_id) {
      return $http.get('/api/v3/cycles/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    filter_groups_factory.get_filter_group = function (pk) {
      var data;
      var params = {
        pk: filter_group_id
      };
      // if (filter_profile_types != null) {
      //   data = {
      //     profile_type: filter_profile_types
      //   };
      // }
      return $http.post('/api/v3/filter_groups/', data, {
        params: params
      }).then(function (response) {
        return response.data;
      });
    };

    filter_groups_factory.new_filter_group_for_org = function (org_id, data) {
      return $http.post('/api/v3/filter_groups/', data, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    // It appears that views/v3/filter_group.py needs to add the following methods

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

    // filter_groups_factory.update_filter_group = function (org_id, id, data) {
    //   return $http.put('/api/v3/filter_groups/' + id + '/', data, {
    //     params: {
    //       organization_id: org_id
    //     }
    //   }).then(function (response) {
    //     return response.data;
    //   });
    // };

    // filter_groups_factory.delete_filter_groups = function (org_id, id) {
    //   return $http.delete('/api/v3/filter_groups/' + id + '/', {
    //     params: {
    //       organization_id: org_id
    //     }
    //   }).then(function (response) {
    //     return response.data;
    //   });
    // };

    return filter_groups_factory;

  }]);
