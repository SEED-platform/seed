/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.pairing_settings', [])
  .controller('pairing_settings_controller', [
    '$scope',
    '$stateParams',
    'pairing_service',
    'import_file_payload',
    'propertyColumns',
    'taxlotColumns',
    function ($scope, $stateParams, pairing_service, import_file_payload, propertyColumns, taxlotColumns) {
      $scope.import_file = import_file_payload.import_file;
      $scope.inventory_type = $stateParams.inventory_type;

      var localStorageKey = 'grid.pairing';
      $scope.propertyColumns = pairing_service.loadPropertyColumns(localStorageKey, propertyColumns);
      $scope.taxlotColumns = pairing_service.loadTaxlotColumns(localStorageKey, taxlotColumns);

      var restorePropertyDefaults = function () {
        pairing_service.removeSettings(localStorageKey + '.properties');
        $scope.propertyColumns = pairing_service.loadPropertyColumns(localStorageKey, propertyColumns);
        _.defer(function () {
          // Set row selection
          $scope.propertyGridApi.selection.clearSelectedRows();
          _.forEach($scope.propertyGridApi.grid.rows, function (row) {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });
      };

      var restoreTaxlotDefaults = function () {
        pairing_service.removeSettings(localStorageKey + '.taxlots');
        $scope.taxlotColumns = pairing_service.loadTaxlotColumns(localStorageKey, taxlotColumns);
        _.defer(function () {
          // Set row selection
          $scope.taxlotGridApi.selection.clearSelectedRows();
          _.forEach($scope.taxlotGridApi.grid.rows, function (row) {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });
      };

      var savePropertySettings = function () {
        $scope.propertyColumns = pairing_service.reorderSettings($scope.propertyColumns);
        pairing_service.savePropertyColumns(localStorageKey, $scope.propertyColumns);
      };

      var saveTaxlotSettings = function () {
        $scope.taxlotColumns = pairing_service.reorderSettings($scope.taxlotColumns);
        pairing_service.saveTaxlotColumns(localStorageKey, $scope.taxlotColumns);
      };

      var propertyRowSelectionChanged = function () {
        _.forEach($scope.propertyGridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
        });
        savePropertySettings();
      };

      var taxlotRowSelectionChanged = function () {
        _.forEach($scope.taxlotGridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
        });
        saveTaxlotSettings();
      };

      $scope.propertyGridOptions = {
        data: 'propertyColumns',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        gridMenuCustomItems: [{
          title: 'Reset defaults',
          action: restorePropertyDefaults
        }],
        gridMenuShowHideColumns: false,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: [{
          name: 'displayName',
          displayName: 'Column Name',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.name $}">{$ COL_FIELD CUSTOM_FILTERS $}</div>',
          enableHiding: false
        }],
        onRegisterApi: function (gridApi) {
          $scope.propertyGridApi = gridApi;
          _.defer(function () {
            // Set row selection
            _.forEach($scope.propertyGridApi.grid.rows, function (row) {
              if (row.entity.visible === false) row.setSelected(false);
              else row.setSelected(true);
            });
          });

          gridApi.selection.on.rowSelectionChanged($scope, propertyRowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, propertyRowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, savePropertySettings);
        }
      };

      $scope.taxlotGridOptions = {
        data: 'taxlotColumns',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        gridMenuCustomItems: [{
          title: 'Reset defaults',
          action: restoreTaxlotDefaults
        }],
        gridMenuShowHideColumns: false,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: [{
          name: 'displayName',
          displayName: 'Column Name',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.name $}">{$ COL_FIELD CUSTOM_FILTERS $}</div>',
          enableHiding: false
        }],
        onRegisterApi: function (gridApi) {
          $scope.taxlotGridApi = gridApi;
          _.defer(function () {
            // Set row selection
            _.forEach($scope.taxlotGridApi.grid.rows, function (row) {
              if (row.entity.visible === false) row.setSelected(false);
              else row.setSelected(true);
            });
          });

          gridApi.selection.on.rowSelectionChanged($scope, taxlotRowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, taxlotRowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, saveTaxlotSettings);
        }
      };
    }]);
