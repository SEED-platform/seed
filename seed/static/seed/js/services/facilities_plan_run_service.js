/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.facilities_plan_run', []).factory('facilities_plan_run_service', [
  '$http',
  'user_service',
  (
    $http,
    user_service
  ) => {
    const facilities_plan_run_service = {};

    facilities_plan_run_service.get_facilities_plan_run_properties = (facilities_plan_run_id, data) => $http.get(`/api/v3/facilities_plan_runs/${facilities_plan_run_id}/properties/`, {
      params: {
        organization_id: user_service.get_organization().id,
        ...data
      }
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_run_service.get_facilities_plan_runs = () => $http.get('/api/v3/facilities_plan_runs/', {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_run_service.create_facilities_plan_run = (data) => $http.post('/api/v3/facilities_plan_runs/',
      data,
      {params: {organization_id: user_service.get_organization().id}
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_run_service.update_facilities_plan_run = (facilities_plan_run_id, data) => $http.put(`/api/v3/facilities_plan_runs/${facilities_plan_run_id}/`,
      data,
      {params: {organization_id: user_service.get_organization().id}
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_run_service.delete_facilities_plan_run = (facilities_plan_run_id) => $http.delete(`/api/v3/facilities_plan_runs/${facilities_plan_run_id}/`,
      {params: {organization_id: user_service.get_organization().id}
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_run_service.run_the_run = (facilities_plan_run_id) => $http.post(`/api/v3/facilities_plan_runs/${facilities_plan_run_id}/run/`,
      {},
      {params: {organization_id: user_service.get_organization().id}
    })
      .then((response) => response.data)
      .catch((response) => response);

    return facilities_plan_run_service;
  }
]);
