/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.salesforce_mapping', []).factory('salesforce_mapping_service', [
  '$http',
  '$log',
  ($http, $log) => {
    // get all salesforce_mappings defined
    const get_salesforce_mappings = (organization_id) => $http
      .get('/api/v3/salesforce_mappings/', {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.salesforce_mappings);

    // retrieve salesforce_mapping
    const get_salesforce_mapping = (organization_id, id) => $http
      .get(`/api/v3/salesforce_mappings/${id}/`, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.salesforce_mapping);

    // delete
    const delete_salesforce_mapping = (organization_id, id) => {
      if (_.isNil(id)) {
        $log.error('#salesforce_mapping_service.get_salesforce_mapping(): id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .delete(`/api/v3/salesforce_mappings/${id}/`, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data);
    };

    // update
    const update_salesforce_mapping = (organization_id, id, data) => $http
      .put(`/api/v3/salesforce_mappings/${id}/`, data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.salesforce_mapping);

    // create
    const new_salesforce_mapping = (organization_id, data) => $http
      .post('/api/v3/salesforce_mappings/', data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.salesforce_mapping);

    const salesforce_mapping_factory = {
      get_salesforce_mappings,
      get_salesforce_mapping,
      delete_salesforce_mapping,
      update_salesforce_mapping,
      new_salesforce_mapping
    };

    return salesforce_mapping_factory;
  }
]);
