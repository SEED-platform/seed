/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.facilities_plan', []).factory('facilities_plan_service', [
  '$http',
  'user_service',
  (
    $http,
    user_service
  ) => {
    const facilities_plan_service = {};

    facilities_plan_service.get_facilities_plan = (facilities_plan_id) => $http.get(`/api/v3/facilities_plans/${facilities_plan_id}/`, {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response)
      .catch((response) => response);

    facilities_plan_service.get_facilities_plans = () => $http.get('/api/v3/facilities_plans/', {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_service.create_facilities_plan = (data) => $http.post(
      '/api/v3/facilities_plans/',
      data,
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_service.update_facilities_plan = (facilities_plan_id, data) => $http.put(
      `/api/v3/facilities_plans/${facilities_plan_id}/`,
      data,
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response.data)
      .catch((response) => response);

    facilities_plan_service.delete_facilities_plan = (facilities_plan_id) => $http.delete(
      `/api/v3/facilities_plans/${facilities_plan_id}/`,
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response.data)
      .catch((response) => response);

    return facilities_plan_service;
  }
]);
