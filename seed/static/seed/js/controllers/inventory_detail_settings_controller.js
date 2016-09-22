/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_settings', [])
  .controller('inventory_detail_settings_controller', [
    '$scope',
    '$window',
    '$uibModalInstance',
    '$stateParams',
    'inventory_service',
    'user_service',
    'all_columns',
    'default_columns',
    function ($scope, $window, $uibModalInstance, $stateParams, inventory_service, user_service, all_columns, default_columns) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id
      };
      $scope.cycle = {
        id: $stateParams.cycle_id
      };

      var restoreDefaults = function () {
        $scope.data = angular.copy(all_columns);
        _.defer($scope.gridApi.selection.selectAllRows);
      };

      var saveSettings = function () {
        var cols = [];
        var count = $scope.gridApi.grid.selection.selectedCount;
        if (count > 0 && count < all_columns.length) {
          cols = _.map($scope.gridApi.selection.getSelectedRows(), 'name');
          $scope.data = inventory_service.reorderBySelected($scope.data, cols);
        }
        localStorage.setItem('grid.' + $scope.inventory_type + '.detail.visible', JSON.stringify(cols));
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.section_header_container', '.section_content.with_padding'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };

      $scope.data = angular.copy(all_columns);
      // Temp code while localStorage is still used:
      var localColumns = localStorage.getItem('grid.' + $scope.inventory_type + '.detail.visible');
      if (!_.isNull(localColumns)) {
        default_columns.columns = JSON.parse(localColumns);
      } else {
        default_columns.columns = [];
      }
      $scope.data = inventory_service.reorderBySelected($scope.data, default_columns.columns);

      $scope.gridOptions = {
        data: 'data',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        gridMenuCustomItems: [{
          title: 'Reset defaults',
          action: restoreDefaults
        }],
        gridMenuShowHideColumns: false,
        minRowsToShow: 30,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: [{
          name: 'displayName',
          displayName: 'Column Name',
          enableHiding: false
        }],
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          if (_.isEmpty(default_columns.columns)) {
            _.defer(gridApi.selection.selectAllRows);
          } else {
            _.defer(function () {
              // Select default rows
              _.forEach($scope.gridApi.grid.rows, function (row) {
                if (row.entity.defaultSelection) row.setSelected(true);
              });
            });
          }

          gridApi.selection.on.rowSelectionChanged($scope, saveSettings);
          gridApi.selection.on.rowSelectionChangedBatch($scope, saveSettings);
          gridApi.draggableRows.on.rowDropped($scope, saveSettings);

          _.delay($scope.updateHeight, 150);
          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };
    }]);
