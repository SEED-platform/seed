/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.pairing', []).factory('pairing_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const pairing_service = {};

    pairing_service.pair_property_to_taxlot = (taxlot_id, property_id) => $http
      .put(
        `/api/v3/taxlots/${taxlot_id}/pair/`,
        {},
        {
          params: {
            organization_id: user_service.get_organization().id,
            property_id
          }
        }
      )
      .then((response) => response.data);

    pairing_service.pair_taxlot_to_property = (property_id, taxlot_id) => $http
      .put(
        `/api/v3/properties/${property_id}/pair/`,
        {},
        {
          params: {
            organization_id: user_service.get_organization().id,
            taxlot_id
          }
        }
      )
      .then((response) => response.data);

    pairing_service.unpair_property_from_taxlot = (taxlot_id, property_id) => $http
      .put(
        `/api/v3/taxlots/${taxlot_id}/unpair/`,
        {},
        {
          params: {
            organization_id: user_service.get_organization().id,
            property_id
          }
        }
      )
      .then((response) => response.data);

    pairing_service.unpair_taxlot_from_property = (property_id, taxlot_id) => $http
      .put(
        `/api/v3/properties/${property_id}/unpair/`,
        {},
        {
          params: {
            organization_id: user_service.get_organization().id,
            taxlot_id
          }
        }
      )
      .then((response) => response.data);

    pairing_service.reorderSettings = (columns) => {
      const selected = _.remove(columns, 'visible');
      return selected.concat(columns);
    };

    pairing_service.removeSettings = (key) => {
      key += `.${user_service.get_organization().id}`;
      localStorage.removeItem(key);
    };

    pairing_service.savePropertyColumns = (key, columns) => {
      key += `.properties.${user_service.get_organization().id}`;
      const toSave = pairing_service.reorderSettings(_.map(columns, (col) => _.pick(col, ['name', 'visible'])));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    pairing_service.loadPropertyColumns = (key, columns) => {
      key += `.properties.${user_service.get_organization().id}`;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, (col) => {
        col.visible = !col.is_extra_data;
      });

      let localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, (col) => !_.find(columns, { name: col.name }));
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, (col) => _.defaults(col, _.remove(columns, { name: col.name })[0]));
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, (col) => {
            col.visible = !col.is_extra_data;
          });
        }
        return pairing_service.reorderSettings(localColumns.concat(columns));
      }
      let filteredColumns = [];
      filteredColumns = filteredColumns.concat(_.remove(columns, { column_name: 'address_line_1', table_name: 'PropertyState' }));
      filteredColumns = filteredColumns.concat(_.remove(columns, { column_name: 'pm_property_id', table_name: 'PropertyState' }));
      filteredColumns = filteredColumns.concat(_.remove(columns, { column_name: 'custom_id_1', table_name: 'PropertyState' }));
      _.forEach(columns, (col) => {
        col.visible = false;
      });
      return pairing_service.reorderSettings(filteredColumns.concat(columns));
    };

    pairing_service.saveTaxlotColumns = (key, columns) => {
      key += `.taxlots.${user_service.get_organization().id}`;
      const toSave = pairing_service.reorderSettings(_.map(columns, (col) => _.pick(col, ['name', 'visible'])));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    pairing_service.loadTaxlotColumns = (key, columns) => {
      key += `.taxlots.${user_service.get_organization().id}`;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, (col) => {
        col.visible = !col.is_extra_data;
      });

      let localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, (col) => !_.find(columns, { name: col.name }));
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, (col) => _.defaults(col, _.remove(columns, { name: col.name })[0]));
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, (col) => {
            col.visible = !col.is_extra_data;
          });
        }
        return pairing_service.reorderSettings(localColumns.concat(columns));
      }
      let filteredColumns = [];
      filteredColumns = filteredColumns.concat(_.remove(columns, { column_name: 'address_line_1', table_name: 'TaxLotState' }));
      filteredColumns = filteredColumns.concat(_.remove(columns, { column_name: 'jurisdiction_tax_lot_id', table_name: 'TaxLotState' }));
      _.forEach(columns, (col) => {
        col.visible = false;
      });
      return pairing_service.reorderSettings(filteredColumns.concat(columns));
    };

    pairing_service.saveSort = (key, settings) => {
      key += `.${user_service.get_organization().id}`;
      localStorage.setItem(key, JSON.stringify(settings));
    };

    pairing_service.loadSort = (key) => {
      key += `.${user_service.get_organization().id}`;
      return localStorage.getItem(key);
    };

    return pairing_service;
  }
]);
