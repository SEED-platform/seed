angular.module('BE.seed.service.audit_template', []).factory('data_view_service', [
  '$http',
  '$log',
  'spinner_utility',
  'user_service',
  function (
    $http,
    $log,
    spinner_utility,
    user_service
  ) {

    const get_data_view = function (data_view_id) {
      if (_.isNil(data_view_id)) {
        $log.error('#data_view_service.get_data_view(): data_view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      spinner_utility.show();
      return $http.get('/api/v3/data_views/' + data_view_id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data_view;
      }).catch(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    const get_data_views = function () {
      spinner_utility.show();
      return $http.get('/api/v3/data_views/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data_views;
      }).catch(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
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
        console.log(response);
        return response.data;
      });
    };

    const data_view_factory = {
      'create_data_view': create_data_view,
      'get_data_view': get_data_view,
      'get_data_views': get_data_views
    };

    return data_view_factory;
  }]);
