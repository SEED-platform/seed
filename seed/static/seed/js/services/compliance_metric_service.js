angular.module('BE.seed.service.compliance_metric', []).factory('compliance_metric_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {

  	// for now assume there is only 1 metric (grab first)
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

   	const compliance_metric_factory = {
      'get_compliance_metrics': get_compliance_metrics,
    };

	return compliance_metric_factory;
  }]);
