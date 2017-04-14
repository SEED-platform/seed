/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.pairing', []).factory('pairing_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var pairing_factory = {};

    pairing_factory.pair_property_to_taxlot = function (taxlot_id, property_id) {
      return $http.put('/api/v2/taxlots/' + taxlot_id + '/pair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          property_id: property_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_factory.pair_taxlot_to_property = function (property_id, taxlot_id) {
      return $http.put('/api/v2/properties/' + property_id + '/pair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          taxlot_id: taxlot_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_factory.unpair_property_from_taxlot = function (taxlot_id, property_id) {
      return $http.put('/api/v2/taxlots/' + taxlot_id + '/unpair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          property_id: property_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_factory.unpair_taxlot_from_property = function (property_id, taxlot_id) {
      return $http.put('/api/v2/properties/' + property_id + '/unpair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          taxlot_id: taxlot_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return pairing_factory;

  }]);
