angular.module('BE.seed.service.salesforce_config', []).factory('salesforce_config_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {

  	// get all salesforce_configs defined
  	const get_salesforce_configs = function () {
      return $http.get('/api/v3/salesforce_configs/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_configs;
      }).catch(function (response) {
        return response.data;
      });
    };

    // retrieve salesforce_config
    const get_salesforce_config = function (id) {
      return $http.get('/api/v3/salesforce_configs/' + id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.salesforce_config;
      }).catch(function (response) {
        return response.data;
      });
    };

    // delete
    const delete_salesforce_config = function (id) {
      if (_.isNil(id)) {
        $log.error('#salesforce_config_service.get_salesforce_config(): id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http.delete('/api/v3/salesforce_configs/' + id + '/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    // update
    const update_salesforce_config = function (id, data, timezone=null) {
      return $http.put('/api/v3/salesforce_configs/' + id + '/', data, {
        params: {
          'organization_id': user_service.get_organization().id,
          'timezone': timezone
        }
      }).then(function (response) {
        return response.data.salesforce_config;
      }).catch(function (response) {
        return response.data;
      });
    };

    // create
    const new_salesforce_config = function (data, timezone=null) {
      return $http.post('/api/v3/salesforce_configs/', data, {
        params: {
          'organization_id': user_service.get_organization().id,
          'timezone': timezone
        }
      }).then(function (response) {
        return response.data.salesforce_config;
      }).catch(function (response) {
        return response.data;
      });
    };

    /**
     * test the Salesforce connection
     * @param {conf} salesforce config object
     */
    const salesforce_connection = function (conf) {
      // todo: check that this works before configs are saved for the first time
      return $http.post('/api/v3/salesforce_configs/' + conf.id + '/salesforce_connection/', {
        salesforce_config: conf
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * automatic sync of properties with Salesforce Benchmarks
    */
    const sync_salesforce = function () {
      // todo: check that this works before configs are saved for the first time
      return $http.post('/api/v3/salesforce_configs/sync/', {
        params: {
          'organization_id': user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    }

    const salesforce_config_factory = {
      'get_salesforce_configs': get_salesforce_configs,
      'get_salesforce_config': get_salesforce_config,
      'delete_salesforce_config': delete_salesforce_config,
      'update_salesforce_config': update_salesforce_config,
      'new_salesforce_config': new_salesforce_config,
      'salesforce_connection': salesforce_connection,
      'sync_salesforce': sync_salesforce
    };

	return salesforce_config_factory;
  }]);
