/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.ubid', []).factory('ubid_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const ubid_factory = {};

    ubid_factory.decode_by_ids = (property_view_ids, taxlot_view_ids) => $http
      .post(
        '/api/v3/ubid/decode_by_ids/',
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
      .then((response) => response);

    ubid_factory.decode_results = (property_view_ids, taxlot_view_ids) => $http
      .post(
        '/api/v3/ubid/decode_results/',
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

    ubid_factory.compare_ubids = (ubid1, ubid2) => $http
      .post(
        '/api/v3/ubid/get_jaccard_index/',
        {
          ubid1,
          ubid2
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    ubid_factory.validate_ubid_js = (ubid) => UniqueBuildingIdentification.v3.isValid(ubid);

    ubid_factory.validate_ubid = (ubid) => $http
      .post(
        '/api/v3/ubid/validate_ubid/',
        {
          ubid
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    ubid_factory.get_ubid_models_by_state = (view_id, state_type) => $http
      .post(
        '/api/v3/ubid/ubids_by_view/',
        {
          view_id,
          type: state_type
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    ubid_factory.create_ubid = (type, state_id, ubid_details) => {
      ubid_details[type] = state_id;
      return $http
        .post('/api/v3/ubid/', ubid_details, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data);
    };

    ubid_factory.delete_ubid = (ubid_id) => $http
      .delete(`/api/v3/ubid/${ubid_id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    ubid_factory.update_ubid = (ubid) => {
      const ubid_details = {
        ubid: ubid.ubid,
        preferred: ubid.preferred
      };
      return $http
        .put(`/api/v3/ubid/${ubid.id}/`, ubid_details, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data);
    };

    return ubid_factory;
  }
]);
