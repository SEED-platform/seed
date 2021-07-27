angular.module('BE.seed.service.geocode', [])
  .factory('geocode_service', [
    '$http',
    'user_service',
    function ($http, user_service) {
      var geocode_factory = {};

      geocode_factory.geocode_by_ids = function (property_view_ids, taxlot_view_ids) {
        return $http.post('/api/v3/geocode/geocode_by_ids/', {
          property_view_ids: property_view_ids,
          taxlot_view_ids: taxlot_view_ids
        }, {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response;
        }).catch(function (e) {
          if (_.includes(e.data, 'MapQuestAPIKeyError')) throw {status: 403, message: 'MapQuestAPIKeyError'};
          else throw e;
        });
      };

      geocode_factory.confidence_summary = function (property_view_ids, taxlot_view_ids) {
        return $http.post('/api/v3/geocode/confidence_summary/', {
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

      geocode_factory.check_org_has_api_key = function (org_id) {
        var params = {organization_id: org_id};
        return $http.get('/api/v3/organizations/' + org_id + '/geocode_api_key_exists/', {
          params: params
        }).then(function (response) {
          return response.data;
        });
      };

      geocode_factory.check_org_has_geocoding_enabled = function (org_id) {
        var params = {organization_id: org_id};
        return $http.get('/api/v3/organizations/' + org_id + '/geocoding_enabled/', {
          params: params
        }).then(function (response) {
          return response.data;
        });
      };

      return geocode_factory;
    }
  ]);
