/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.pairing_settings', []).controller('pairing_settings_controller', [
  '$scope',
  '$stateParams',
  'pairing_service',
  'import_file_payload',
  'propertyColumns',
  'taxlotColumns',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, pairing_service, import_file_payload, propertyColumns, taxlotColumns) {
    $scope.import_file = import_file_payload.import_file;
    $scope.inventory_type = $stateParams.inventory_type;

    const localStorageKey = 'grid.pairing';
    $scope.propertyColumns = pairing_service.loadPropertyColumns(localStorageKey, propertyColumns);
    $scope.taxlotColumns = pairing_service.loadTaxlotColumns(localStorageKey, taxlotColumns);

    const restorePropertyDefaults = function () {
      pairing_service.removeSettings(`${localStorageKey}.properties`);
      $scope.propertyColumns = pairing_service.loadPropertyColumns(localStorageKey, propertyColumns);
      _.defer(() => {
        // Set row selection
        $scope.propertyGridApi.selection.clearSelectedRows();
        _.forEach($scope.propertyGridApi.grid.rows, (row) => {
          if (row.entity.visible === false) row.setSelected(false);
          else row.setSelected(true);
        });
      });
    };

    const restoreTaxlotDefaults = function () {
      pairing_service.removeSettings(`${localStorageKey}.taxlots`);
      $scope.taxlotColumns = pairing_service.loadTaxlotColumns(localStorageKey, taxlotColumns);
      _.defer(() => {
        // Set row selection
        $scope.taxlotGridApi.selection.clearSelectedRows();
        _.forEach($scope.taxlotGridApi.grid.rows, (row) => {
          if (row.entity.visible === false) row.setSelected(false);
          else row.setSelected(true);
        });
      });
    };

    const savePropertySettings = function () {
      $scope.propertyColumns = pairing_service.reorderSettings($scope.propertyColumns);
      pairing_service.savePropertyColumns(localStorageKey, $scope.propertyColumns);
    };

    const saveTaxlotSettings = function () {
      $scope.taxlotColumns = pairing_service.reorderSettings($scope.taxlotColumns);
      pairing_service.saveTaxlotColumns(localStorageKey, $scope.taxlotColumns);
    };

    const propertyRowSelectionChanged = function () {
      _.forEach($scope.propertyGridApi.grid.rows, (row) => {
        row.entity.visible = row.isSelected;
      });
      savePropertySettings();
    };

    const taxlotRowSelectionChanged = function () {
      _.forEach($scope.taxlotGridApi.grid.rows, (row) => {
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
      gridMenuCustomItems: [
        {
          title: 'Reset defaults',
          action: restorePropertyDefaults
        }
      ],
      gridMenuShowHideColumns: false,
      rowTemplate:
        '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
      columnDefs: [
        {
          name: 'displayName',
          displayName: 'Column Name',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.name $}">{$ COL_FIELD CUSTOM_FILTERS $}</div>',
          enableHiding: false
        }
      ],
      onRegisterApi(gridApi) {
        $scope.propertyGridApi = gridApi;
        _.defer(() => {
          // Set row selection
          _.forEach($scope.propertyGridApi.grid.rows, (row) => {
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
      gridMenuCustomItems: [
        {
          title: 'Reset defaults',
          action: restoreTaxlotDefaults
        }
      ],
      gridMenuShowHideColumns: false,
      rowTemplate:
        '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
      columnDefs: [
        {
          name: 'displayName',
          displayName: 'Column Name',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.name $}">{$ COL_FIELD CUSTOM_FILTERS $}</div>',
          enableHiding: false
        }
      ],
      onRegisterApi(gridApi) {
        $scope.taxlotGridApi = gridApi;
        _.defer(() => {
          // Set row selection
          _.forEach($scope.taxlotGridApi.grid.rows, (row) => {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });

        gridApi.selection.on.rowSelectionChanged($scope, taxlotRowSelectionChanged);
        gridApi.selection.on.rowSelectionChangedBatch($scope, taxlotRowSelectionChanged);
        gridApi.draggableRows.on.rowDropped($scope, saveTaxlotSettings);
      }
    };
  }
]);
