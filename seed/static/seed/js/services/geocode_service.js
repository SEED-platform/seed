/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.geocode', []).factory('geocode_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const geocode_factory = {};

    geocode_factory.geocode_by_ids = (property_view_ids, taxlot_view_ids) => $http
      .post(
        '/api/v3/geocode/geocode_by_ids/',
        {
          property_view_ids,
          taxlot_view_ids
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response)
      .catch((e) => {
        if (_.includes(e.data, 'MapQuestAPIKeyError')) throw { status: 403, message: 'MapQuestAPIKeyError' };
        else throw e;
      });

    geocode_factory.confidence_summary = (property_view_ids, taxlot_view_ids) => $http
      .post(
        '/api/v3/geocode/confidence_summary/',
        {
          property_view_ids,
          taxlot_view_ids
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    geocode_factory.check_org_has_api_key = (org_id) => {
      const params = { organization_id: org_id };
      return $http
        .get(`/api/v3/organizations/${org_id}/geocode_api_key_exists/`, {
          params
        })
        .then((response) => response.data);
    };

    geocode_factory.check_org_has_geocoding_enabled = (org_id) => {
      const params = { organization_id: org_id };
      return $http
        .get(`/api/v3/organizations/${org_id}/geocoding_enabled/`, {
          params
        })
        .then((response) => response.data);
    };

    return geocode_factory;
  }
]);
