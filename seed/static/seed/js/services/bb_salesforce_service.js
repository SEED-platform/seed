angular.module('SEED.service.bb_salesforce', []).factory('bb_salesforce_service', [
  '$http',
  '$log',
  ($http, $log) => {
    // get bb_salesforce_configs
    const get_bb_salesforce_configs = (organization_id) => $http
      .get('/api/v3/bb_salesforce/configs/', {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.bb_salesforce_configs)
      .catch((response) => response.data);

    // delete
    const delete_bb_salesforce_config = (organization_id, id) => {
      if (_.isNil(id)) {
        $log.error('#salesforce_config_service.get_salesforce_config(): id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .delete(`/api/v3/bb_salesforce/configs/${id}/`, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    // update
    const update_bb_salesforce_config = (organization_id, data, timezone = null) => $http
      .put(`/api/v3/bb_salesforce/configs/update_config/`, data, {
        params: {
          organization_id,
          timezone
        }
      })
      .then((response) => response.data.bb_salesforce_configs)
      .catch((response) => response.data);

    // create
    const new_bb_salesforce_config = (organization_id, data, timezone = null) => $http
      .post('/api/v3/bb_salesforce/configs/', data, {
        params: {
          organization_id,
          timezone
        }
      })
      .then((response) => response.data.bb_salesforce_configs)
      .catch((response) => response.data);

    const get_login_url = (
      organization_id
    ) => $http
      .get('/api/v3/bb_salesforce/login_url/', {
        params: {
          organization_id
        }
      })
      .then((response) => response.data);

    const get_token = (
      code,
      organization_id
    ) => $http
      .get('/api/v3/bb_salesforce/get_token/', {
        params: {
          organization_id,
          code
        }
      })
      .then((response) => response.data);

    const verify_token = (
      organization_id
    ) => $http
      .get('/api/v3/bb_salesforce/verify_token/', {
        params: {
          organization_id,
        }
      })

    const get_partners = (
      organization_id
    ) => $http
      .get('/api/v3/bb_salesforce/partners/', {
        params: {
          organization_id,
        }
      })
      .then((response) => response.data);

    const get_annual_report = (
      organization_id,
      goal_id,
    ) => $http
      .get('/api/v3/bb_salesforce/annual_report/', {
        params: {
          organization_id,
          goal_id,
        }
      })
      .then((response) => response.data);

    const salesforce_config_factory = {
      get_bb_salesforce_configs,
      delete_bb_salesforce_config,
      update_bb_salesforce_config,
      new_bb_salesforce_config,
      get_login_url,
      get_token,
      verify_token,
      get_partners,
      get_annual_report
    };

    return salesforce_config_factory;
  }
]);
