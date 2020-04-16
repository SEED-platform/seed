angular.module('BE.seed.service.geocode', [])
  .factory('geocode_service', [
    '$http',
    'user_service',
    function ($http, user_service) {
      var geocode_factory = {};

      geocode_factory.geocode_by_ids = function (property_state_ids, taxlot_state_ids) {
        return $http.post('/api/v2/geocode/geocode_by_ids/', {
          property_ids: property_state_ids,
          taxlot_ids: taxlot_state_ids
        }, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response;
        });
      };

      geocode_factory.confidence_summary = function (property_state_ids, taxlot_state_ids) {
        return $http.post('/api/v2/geocode/confidence_summary/', {
          property_ids: property_state_ids,
          tax_lot_ids: taxlot_state_ids
        }).then(function (response) {
          return response.data;
        });
      };

      geocode_factory.check_org_has_api_key = function (org_id) {
        var params = {organization_id: org_id};
        return $http.get('/api/v2/geocode/api_key_exists', {
          params: params
        }).then(function (response) {
          return response.data;
        });
      };

      return geocode_factory;
    }
  ]);
