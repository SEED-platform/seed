/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_settings', [])
  .controller('matching_settings_controller', [
    '$scope',
    '$stateParams',
    'matching_service',
    'import_file_payload',
    'columns',
    function ($scope, $stateParams, matching_service, import_file_payload, columns) {
      $scope.import_file = import_file_payload.import_file;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id
      };
      $scope.cycle = {
        id: $stateParams.cycle_id
      };

      var localStorageKey = 'grid.matching.' + $scope.inventory_type;
      $scope.columns = columns;
      $scope.leftColumns = matching_service.loadLeftColumns(localStorageKey, columns);
      $scope.mappedColumnsOnly = $scope.leftColumns === 'showOnlyMappedFields';

      $scope.rightColumns = matching_service.loadRightColumns(localStorageKey, _.reject(columns, {extraData: true}));

      var restoreLeftDefaults = function () {
        matching_service.removeLeftSettings(localStorageKey);
        $scope.leftColumns = matching_service.loadLeftColumns(localStorageKey, columns);
        _.defer(function () {
          // Set row selection
          $scope.leftGridApi.selection.clearSelectedRows();
          _.forEach($scope.leftGridApi.grid.rows, function (row) {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });
      };

      var restoreRightDefaults = function () {
        matching_service.removeRightSettings(localStorageKey);
        $scope.rightColumns = matching_service.loadRightColumns(localStorageKey, columns);
        _.defer(function () {
          // Set row selection
          $scope.rightGridApi.selection.clearSelectedRows();
          _.forEach($scope.rightGridApi.grid.rows, function (row) {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });
      };

      var saveLeftSettings = function () {
        $scope.leftColumns = matching_service.reorderSettings($scope.leftColumns);
        matching_service.saveLeftColumns(localStorageKey, $scope.leftColumns);
      };

      var saveRightSettings = function () {
        $scope.rightColumns = matching_service.reorderSettings($scope.rightColumns);
        matching_service.saveRightColumns(localStorageKey, $scope.rightColumns);
      };

      var leftRowSelectionChanged = function () {
        _.forEach($scope.leftGridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
        });
        saveLeftSettings();
      };

      var rightRowSelectionChanged = function (row) {
        _.forEach($scope.rightGridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
        });
        saveRightSettings();
      };

      $scope.toggleMappedColumnsOnly = function () {
        $scope.mappedColumnsOnly = !$scope.mappedColumnsOnly;
        matching_service.saveShowOnlyMappedFields($scope.mappedColumnsOnly);

        $scope.leftColumns = matching_service.loadLeftColumns(localStorageKey, columns);
        $scope.mappedColumnsOnly = $scope.leftColumns === 'showOnlyMappedFields';
      };

      $scope.leftGridOptions = {
        data: 'leftColumns',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        gridMenuCustomItems: [{
          title: 'Reset defaults',
          action: restoreLeftDefaults
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
          $scope.leftGridApi = gridApi;
          _.defer(function () {
            // Set row selection
            _.forEach($scope.leftGridApi.grid.rows, function (row) {
              if (row.entity.visible === false) row.setSelected(false);
              else row.setSelected(true);
            });
          });

          gridApi.selection.on.rowSelectionChanged($scope, leftRowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, leftRowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, saveLeftSettings);
        }
      };

      $scope.rightGridOptions = {
        data: 'rightColumns',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        gridMenuCustomItems: [{
          title: 'Reset defaults',
          action: restoreRightDefaults
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
          $scope.rightGridApi = gridApi;
          _.defer(function () {
            // Set row selection
            _.forEach($scope.rightGridApi.grid.rows, function (row) {
              if (row.entity.visible === false) row.setSelected(false);
              else row.setSelected(true);
            });
          });

          gridApi.selection.on.rowSelectionChanged($scope, rightRowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, rightRowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, saveRightSettings);
        }
      };
    }]);
