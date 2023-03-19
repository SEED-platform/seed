angular.module('BE.seed.service.salesforce_mapping', []).factory('salesforce_mapping_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {

  	// get all salesforce_mappings defined
  	const get_salesforce_mappings = function () {
      return $http.get('/api/v3/salesforce_mappings/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_mappings;
      });
    };

    // retrieve salesforce_mapping
    const get_salesforce_mapping = function (id) {
      return $http.get('/api/v3/salesforce_mappings/' + id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_mapping;
      });
    };

    // delete
    const delete_salesforce_mapping = function (id) {
      if (_.isNil(id)) {
        $log.error('#salesforce_mapping_service.get_salesforce_mapping(): id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http.delete('/api/v3/salesforce_mappings/' + id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    // update
    const update_salesforce_mapping = function (id, data) {
      return $http.put('/api/v3/salesforce_mappings/' + id + '/', data, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_mapping;
      });
    };

    // create
    const new_salesforce_mapping = function (data) {
      return $http.post('/api/v3/salesforce_mappings/', data, {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_mapping;
      });
    };

    const salesforce_mapping_factory = {
      'get_salesforce_mappings': get_salesforce_mappings,
      'get_salesforce_mapping': get_salesforce_mapping,
      'delete_salesforce_mapping': delete_salesforce_mapping,
      'update_salesforce_mapping': update_salesforce_mapping,
      'new_salesforce_mapping': new_salesforce_mapping
    };

	return salesforce_mapping_factory;
  }]);
