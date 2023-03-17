/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.ubid', [])
  .factory('ubid_service', [
    '$http',
    'user_service',
    function ($http, user_service) {
      var ubid_factory = {};

      ubid_factory.decode_by_ids = function (property_view_ids, taxlot_view_ids) {
        return $http.post('/api/v3/ubid/decode_by_ids/', {
          property_view_ids: property_view_ids,
          taxlot_view_ids: taxlot_view_ids
        }, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response;
        });
      };

      ubid_factory.decode_results = function (property_view_ids, taxlot_view_ids) {
        return $http.post('/api/v3/ubid/decode_results/', {
          property_view_ids: property_view_ids,
          taxlot_view_ids: taxlot_view_ids
        }, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data;
        });
      };

      return ubid_factory;
    }
  ]);
