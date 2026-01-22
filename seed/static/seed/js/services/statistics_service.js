angular.module('SEED.service.statistics', []).factory('statistics_service', [
  '$http',
  ($http) => {
    // get all statistics for org (should just be 1)
    const get_statistics = (organization_id) => $http
      .get('/api/v3/statistics/', {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.statistics)
      .catch((response) => response.data);

    // retrieve statistic by ID
    const get_statistic = (organization_id, id) => $http
      .get(`/api/v3/statistics/${id}/`, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.statistic)
      .catch((response) => response.data);

    // update
    const update_statistic = (organization_id, id, data) => $http
      .put(`/api/v3/statistics/${id}/`, data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.statistic)
      .catch((response) => response.data);

    // create
    const new_statistic = (organization_id, data) => $http
      .post('/api/v3/statistics/', data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.statistic)
      .catch((response) => response.data);

    // calculate statistics
    const calculate_statistics = (organization_id, id) => $http
      .post(`/api/v3/statistics/${id}/calculate/`, null, {
        params: {
          organization_id
        }
      })
      .then((response) => response)
      .catch((response) => response);

    const statistics_factory = {
      get_statistics,
      get_statistic,
      update_statistic,
      new_statistic,
      calculate_statistics
    };

    return statistics_factory;
  }
]);
