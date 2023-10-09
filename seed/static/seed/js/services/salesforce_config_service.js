angular.module('BE.seed.service.salesforce_config', []).factory('salesforce_config_service', [
  '$http',
  '$log',
  function ($http, $log) {
    // get all salesforce_configs defined
    const get_salesforce_configs = (organization_id) =>
      $http
        .get('/api/v3/salesforce_configs/', {
          params: {
            organization_id
          }
        })
        .then((response) => response.data.salesforce_configs)
        .catch((response) => response.data);

    // retrieve salesforce_config
    const get_salesforce_config = (organization_id, id) =>
      $http
        .get(`/api/v3/salesforce_configs/${id}/`, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data.salesforce_config)
        .catch((response) => response.data);

    // delete
    const delete_salesforce_config = function (organization_id, id) {
      if (_.isNil(id)) {
        $log.error('#salesforce_config_service.get_salesforce_config(): id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .delete(`/api/v3/salesforce_configs/${id}/`, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    // update
    const update_salesforce_config = (organization_id, id, data, timezone = null) =>
      $http
        .put(`/api/v3/salesforce_configs/${id}/`, data, {
          params: {
            organization_id,
            timezone
          }
        })
        .then((response) => response.data.salesforce_config)
        .catch((response) => response.data);

    // create
    const new_salesforce_config = (organization_id, data, timezone = null) =>
      $http
        .post('/api/v3/salesforce_configs/', data, {
          params: {
            organization_id,
            timezone
          }
        })
        .then((response) => response.data.salesforce_config)
        .catch((response) => response.data);

    /**
     * test the Salesforce connection
     * @param {obj} conf - salesforce config object
     */
    const salesforce_connection = (organization_id, conf) =>
      $http
        .post(
          '/api/v3/salesforce_configs/salesforce_connection/',
          {
            salesforce_config: conf
          },
          {
            params: {
              organization_id
            }
          }
        )
        .then((response) => response.data);

    /**
     * automatic sync of properties with Salesforce Benchmarks
     */
    const sync_salesforce = (
      organization_id // todo: check that this works before configs are saved for the first time
    ) =>
      $http
        .post('/api/v3/salesforce_configs/sync/', undefined, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data);

    const salesforce_config_factory = {
      get_salesforce_configs,
      get_salesforce_config,
      delete_salesforce_config,
      update_salesforce_config,
      new_salesforce_config,
      salesforce_connection,
      sync_salesforce
    };

    return salesforce_config_factory;
  }
]);
