/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.goal', []).factory('goal_service', [
  '$http',
  'user_service',
  (
    $http,
    user_service
  ) => {
    const goal_service = {};

    goal_service.create_goal = (goal) => $http.post('/api/v3/goals/', goal)
      .then((response) => response)
      .catch((response) => response);

    goal_service.update_goal = (goal) => $http.put(`/api/v3/goals/${goal.id}/`, goal)
      .then((response) => response)
      .catch((response) => response);

    goal_service.get_goal = (goal_id) => $http.get(`/api/v3/goals/${goal_id}/`, {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response)
      .catch((response) => response);

    goal_service.get_goals = () => $http.get('/api/v3/goals/', {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response.data)
      .catch((response) => response);

    goal_service.delete_goal = (goal_id) => $http.delete(`/api/v3/goals/${goal_id}`, {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response)
      .catch((response) => response);

    goal_service.get_portfolio_summary = (goal_id) => $http.get(`/api/v3/goals/${goal_id}/portfolio_summary/`, {
      params: {
        organization_id: user_service.get_organization().id
      }
    })
      .then((response) => response)
      .catch((response) => response);

    goal_service.update_historical_note = (property, historical_note, data) => {
      data.property = property;
      return $http.put(
        `/api/v3/properties/${property}/historical_notes/${historical_note}/`,
        data,
        { params: { organization_id: user_service.get_organization().id } }
      )
        .then((response) => response)
        .catch((response) => response);
    };

    goal_service.update_goal_note = (property, goal_note, data) => $http.put(
      `/api/v3/properties/${property}/goal_notes/${goal_note}/`,
      data,
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response)
      .catch((response) => response);

    goal_service.bulk_update_goal_note = (property_view_ids, goal, data) => $http.put(
      `/api/v3/goals/${goal.id}/bulk_update_goal_notes/`,
      { data, property_view_ids },
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response)
      .catch((response) => response);

    return goal_service;
  }
]);
