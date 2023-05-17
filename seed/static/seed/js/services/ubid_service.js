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

      ubid_factory.compare_ubids = (property_view_ids, taxlot_view_ids) => {
        return $http.post('/api/v3/ubid/get_jaccard_index/', {
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

      ubid_factory.get_ubid_models_by_state = (view_id, state_type) => {
        return $http.post('/api/v3/ubid/ubids_by_state/', {
          view_id: view_id,
          type: state_type
        }, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data
        })
      }
      
      ubid_factory.create_ubid = (type, state_id, ubid_details) => {
        ubid_details[type] = state_id
        return $http.post('/api/v3/ubid/',
          ubid_details, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data
        })
      }

      ubid_factory.delete_ubid = (ubid_id) => {
        return $http.delete(`/api/v3/ubid/${ubid_id}`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data
        })
      }

      return ubid_factory;
    }
  ]);
