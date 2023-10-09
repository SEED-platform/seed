/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.compliance_metric', []).factory('compliance_metric_service', [
  '$http',
  '$log',
  'user_service',
  // eslint-disable-next-line func-names
  function ($http, $log, user_service) {
    // get all compliance metrics defined
    const get_compliance_metrics = (organization_id = user_service.get_organization().id) => $http
      .get('/api/v3/compliance_metrics/', {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.compliance_metrics)
      .catch((response) => response.data);

    // retrieve compliance metric
    const get_compliance_metric = (metric_id, organization_id = user_service.get_organization().id) => $http
      .get(`/api/v3/compliance_metrics/${metric_id}/`, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.compliance_metric)
      .catch((response) => response.data);

    // delete
    const delete_compliance_metric = function (metric_id, organization_id = user_service.get_organization().id) {
      if (_.isNil(metric_id)) {
        $log.error('#compliance_metric_service.get_compliance_metric(): metric_id is undefined');
        throw new Error('Invalid Parameter');
      }
      return $http
        .delete(`/api/v3/compliance_metrics/${metric_id}/`, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    // evaluate
    const evaluate_compliance_metric = (metric_id, organization_id = user_service.get_organization().id) => $http
      .get(`/api/v3/compliance_metrics/${metric_id}/evaluate/`, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.data)
      .catch((response) => response.data);

    // update
    const update_compliance_metric = (metric_id, data, organization_id = user_service.get_organization().id) => $http
      .put(`/api/v3/compliance_metrics/${metric_id}/`, data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.compliance_metric)
      .catch((response) => response.data);

    // create
    const new_compliance_metric = (data, organization_id = user_service.get_organization().id) => $http
      .post('/api/v3/compliance_metrics/', data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.compliance_metric)
      .catch((response) => response.data);

    return {
      get_compliance_metrics,
      get_compliance_metric,
      delete_compliance_metric,
      evaluate_compliance_metric,
      update_compliance_metric,
      new_compliance_metric
    };
  }
]);
