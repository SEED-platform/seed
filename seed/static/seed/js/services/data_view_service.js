/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.data_view', []).factory('data_view_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {

    const get_data_view = function (data_view_id) {
      if (_.isNil(data_view_id)) {
        $log.error('#data_view_service.get_data_view(): data_view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http.get('/api/v3/data_views/' + data_view_id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data_view;
      }).catch(function (response) {
        return response.data;
      });
    };

    const get_data_views = function () {
      return $http.get('/api/v3/data_views/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data_views;
      }).catch(function (response) {
        return response.data;
      });
    };

    const create_data_view = function (name, filter_groups, cycles, data_aggregations) {
      return $http.post('/api/v3/data_views/', {
        'name': name,
        'filter_groups': filter_groups,
        'cycles': cycles,
        'parameters': data_aggregations
      }, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    const update_data_view = function (id, name, filter_groups, cycles, data_aggregations) {
      return $http.put('/api/v3/data_views/' + id + '/', {
        'name': name,
        'filter_groups': filter_groups,
        'cycles': cycles,
        'parameters': data_aggregations
      }, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    const delete_data_view = function (data_view_id) {
      if (_.isNil(data_view_id)) {
        $log.error('#data_view_service.get_data_view(): data_view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http.delete('/api/v3/data_views/' + data_view_id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    const evaluate_data_view = function (data_view_id, columns) {
      return $http.put('/api/v3/data_views/' + data_view_id + '/evaluate/', {
        'columns': columns
      }, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    const data_view_factory = {
      'create_data_view': create_data_view,
      'delete_data_view': delete_data_view,
      'evaluate_data_view': evaluate_data_view,
      'get_data_view': get_data_view,
      'get_data_views': get_data_views,
      'update_data_view': update_data_view
    };

    return data_view_factory;
  }]);
