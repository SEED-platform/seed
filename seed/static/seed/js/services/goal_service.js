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

    // should this be moved to data_report service?
    goal_service.bulk_update_goal_note = (property_view_ids, goal, data) => $http.put( 
      `/api/v3/goals/${goal.id}/bulk_update_goal_notes/`,
      { data, property_view_ids },
      { params: { organization_id: user_service.get_organization().id } }
    )
      .then((response) => response)
      .catch((response) => response);

    const format_column_filters = (column_filters) => {
      if (!column_filters) {
        return {};
      }
      const filters = {};
      for (const { name, operator, value } of column_filters) {
        filters[`${name}__${operator}`] = value;
      }
      return filters;
    };

    const format_column_sorts = (column_sorts) => {
      if (!column_sorts) {
        return [];
      }

      const result = [];
      for (const { name, direction } of column_sorts) {
        const direction_operator = direction === 'desc' ? '-' : '';
        result.push(`${direction_operator}${name}`);
      }

      return { order_by: result };
    };

    goal_service.load_data = (data, filters, sorts) => {
      const params = {
        organization_id: user_service.get_organization().id,
        ...format_column_filters(filters),
        ...format_column_sorts(sorts)
      };
      return $http.put(
        `/api/v3/data_reports/${data.data_report_id}/goals/${data.goal_id}/data/`,
        data,
        { params }
      )
        .then((response) => response)
        .catch((response) => response);
    };

    return goal_service;
  }
]);
