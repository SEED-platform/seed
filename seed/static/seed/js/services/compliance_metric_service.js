/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.compliance_metric', []).factory('compliance_metric_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {

  	// get all compliance metrics defined
  	const get_compliance_metrics = function (organization_id = user_service.get_organization().id) {
      return $http.get('/api/v3/compliance_metrics/', {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data.compliance_metrics;
      }).catch(function (response) {
        return response.data;
      });
    };

    // retrieve compliance metric
    const get_compliance_metric = function (metric_id, organization_id = user_service.get_organization().id) {
      return $http.get('/api/v3/compliance_metrics/' + metric_id + '/', {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    // delete
    const delete_compliance_metric = function (metric_id, organization_id = user_service.get_organization().id) {
      if (_.isNil(metric_id)) {
        $log.error('#compliance_metric_service.get_compliance_metric(): metric_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http.delete('/api/v3/compliance_metrics/' + metric_id + '/', {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    // evaluate
    const evaluate_compliance_metric = function (metric_id, organization_id = user_service.get_organization().id) {
      return $http.get('/api/v3/compliance_metrics/' + metric_id + '/evaluate/', {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    // update
    const update_compliance_metric = function (metric_id, data, organization_id = user_service.get_organization().id) {
      return $http.put('/api/v3/compliance_metrics/' + metric_id + '/', data, {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    // create
    const new_compliance_metric = function (data, organization_id = user_service.get_organization().id) {
      return $http.post('/api/v3/compliance_metrics/', data, {
        params: {
          organization_id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    return {
      get_compliance_metrics,
      get_compliance_metric,
      delete_compliance_metric,
      evaluate_compliance_metric,
      update_compliance_metric,
      new_compliance_metric
    };
  }]);
