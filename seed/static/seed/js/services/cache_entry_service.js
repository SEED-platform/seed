/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.cache_entry', []).factory('cache_entry_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const cache_entry_service = {};

    cache_entry_service.get_cache_entry = (unique_id) => $http.get(
      `/api/v3/cache_entries/${unique_id}/`,
      {
        params: {
          organization_id: user_service.get_organization().id
        }
      }
    ).then((response) => response.data);

    return cache_entry_service;
  }
]);
