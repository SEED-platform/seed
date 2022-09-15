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
  	const get_compliance_metrics = function () {
      return $http.get('/api/v3/compliance_metrics/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.compliance_metrics;
      }).catch(function (response) {
        return response.data;
      });
    };

    // retrieve compliance metric
    const get_compliance_metric = function (metric_id) {
      return $http.get('/api/v3/compliance_metrics/' + metric_id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    // evaluate
    const evaluate_compliance_metric = function (metric_id) {
      return $http.get('/api/v3/compliance_metrics/' + metric_id + '/evaluate/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    // update
    const update_compliance_metric = function (metric_id, data) {
      return $http.put('/api/v3/compliance_metrics/' + metric_id + '/', data, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    // create
    const new_compliance_metric = function (data) {
      return $http.post('/api/v3/compliance_metrics/', data, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.compliance_metric;
      }).catch(function (response) {
        return response.data;
      });
    };

    const compliance_metric_factory = {
      'get_compliance_metrics': get_compliance_metrics,
      'get_compliance_metric': get_compliance_metric,
      'evaluate_compliance_metric': evaluate_compliance_metric,
      'update_compliance_metric': update_compliance_metric,
      'new_compliance_metric': new_compliance_metric
    };

	return compliance_metric_factory;
  }]);
