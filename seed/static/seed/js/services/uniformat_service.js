/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.uniformat', []).factory('uniformat_service', [
  '$http',
  ($http) => ({
    // Return all uniformat categories
    get_uniformat: () => $http
      .get('/api/v3/uniformat/').then(({ data }) => data.reduce((acc, element) => {
        const { id, ...rest } = element;
        acc[id] = rest;
        return acc;
      }, {}))
  })
]);
