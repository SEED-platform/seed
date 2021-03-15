/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.pairing', []).factory('pairing_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var pairing_service = {};

    pairing_service.pair_property_to_taxlot = function (taxlot_id, property_id) {
      return $http.put('/api/v3/taxlots/' + taxlot_id + '/pair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          property_id: property_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_service.pair_taxlot_to_property = function (property_id, taxlot_id) {
      return $http.put('/api/v3/properties/' + property_id + '/pair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          taxlot_id: taxlot_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_service.unpair_property_from_taxlot = function (taxlot_id, property_id) {
      return $http.put('/api/v3/taxlots/' + taxlot_id + '/unpair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          property_id: property_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_service.unpair_taxlot_from_property = function (property_id, taxlot_id) {
      return $http.put('/api/v3/properties/' + property_id + '/unpair/', {}, {
        params: {
          organization_id: user_service.get_organization().id,
          taxlot_id: taxlot_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    pairing_service.reorderSettings = function (columns) {
      var selected = _.remove(columns, 'visible');
      return selected.concat(columns);
    };

    pairing_service.removeSettings = function (key) {
      key += '.' + user_service.get_organization().id;
      localStorage.removeItem(key);
    };

    pairing_service.savePropertyColumns = function (key, columns) {
      key += '.properties.' + user_service.get_organization().id;
      var toSave = pairing_service.reorderSettings(_.map(columns, function (col) {
        return _.pick(col, ['name', 'visible']);
      }));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    pairing_service.loadPropertyColumns = function (key, columns) {
      key += '.properties.' + user_service.get_organization().id;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, function (col) {
        col.visible = !col.is_extra_data;
      });

      var localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, function (col) {
          return !_.find(columns, {name: col.name});
        });
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, function (col) {
          return _.defaults(col, _.remove(columns, {name: col.name})[0]);
        });
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, function (col) {
            col.visible = !col.is_extra_data;
          });
        }
        return pairing_service.reorderSettings(localColumns.concat(columns));
      } else {
        var filteredColumns = [];
        filteredColumns = filteredColumns.concat(_.remove(columns, {column_name: 'address_line_1', table_name: 'PropertyState'}));
        filteredColumns = filteredColumns.concat(_.remove(columns, {column_name: 'pm_property_id', table_name: 'PropertyState'}));
        filteredColumns = filteredColumns.concat(_.remove(columns, {column_name: 'custom_id_1', table_name: 'PropertyState'}));
        _.forEach(columns, function (col) {
          col.visible = false;
        });
        return pairing_service.reorderSettings(filteredColumns.concat(columns));
      }
    };

    pairing_service.saveTaxlotColumns = function (key, columns) {
      key += '.taxlots.' + user_service.get_organization().id;
      var toSave = pairing_service.reorderSettings(_.map(columns, function (col) {
        return _.pick(col, ['name', 'visible']);
      }));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    pairing_service.loadTaxlotColumns = function (key, columns) {
      key += '.taxlots.' + user_service.get_organization().id;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, function (col) {
        col.visible = !col.is_extra_data;
      });

      var localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, function (col) {
          return !_.find(columns, {name: col.name});
        });
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, function (col) {
          return _.defaults(col, _.remove(columns, {name: col.name})[0]);
        });
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, function (col) {
            col.visible = !col.is_extra_data;
          });
        }
        return pairing_service.reorderSettings(localColumns.concat(columns));
      } else {
        var filteredColumns = [];
        filteredColumns = filteredColumns.concat(_.remove(columns, {column_name: 'address_line_1', table_name: 'TaxLotState'}));
        filteredColumns = filteredColumns.concat(_.remove(columns, {column_name: 'jurisdiction_tax_lot_id', table_name: 'TaxLotState'}));
        _.forEach(columns, function (col) {
          col.visible = false;
        });
        return pairing_service.reorderSettings(filteredColumns.concat(columns));
      }
    };

    pairing_service.saveSort = function (key, settings) {
      key += '.' + user_service.get_organization().id;
      localStorage.setItem(key, JSON.stringify(settings));
    };

    pairing_service.loadSort = function (key) {
      key += '.' + user_service.get_organization().id;
      return localStorage.getItem(key);
    };

    return pairing_service;

  }]);
