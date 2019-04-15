angular.module('BE.seed.service.ubid', [])
  .factory('ubid_service', [
    '$http',
    function ($http) {
      var ubid_factory = {};

      ubid_factory.decode_by_ids = function (property_state_ids, taxlot_state_ids) {
        return $http.post('/api/v2/ubid/decode_by_ids/', {
          property_ids: property_state_ids,
          taxlot_ids: taxlot_state_ids
        }).then(function (response) {
          return response;
        });
      };

      ubid_factory.decode_results = function (property_state_ids, taxlot_state_ids) {
        return $http.post('/api/v2/ubid/decode_results/', {
          property_ids: property_state_ids,
          taxlot_ids: taxlot_state_ids
        }).then(function (response) {
          return response.data;
        });
      };

      return ubid_factory;
    }
  ]);
