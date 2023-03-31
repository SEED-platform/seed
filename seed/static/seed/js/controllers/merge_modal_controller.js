/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.merge_modal', [])
  .controller('merge_modal_controller', [
    '$log',
    '$scope',
    '$uibModal',
    '$uibModalInstance',
    'columns',
    'data',
    'has_meters',
    'inventory_type',
    'matching_service',
    'naturalSort',
    'Notification',
    'org_id',
    'spinner_utility',
    'uiGridConstants',
    'urls',
    function (
      $log,
      $scope,
      $uibModal,
      $uibModalInstance,
      columns,
      data,
      has_meters,
      inventory_type,
      matching_service,
      naturalSort,
      Notification,
      org_id,
      spinner_utility,
      uiGridConstants,
      urls
    ) {
      spinner_utility.hide();

      $scope.inventory_type = inventory_type;
      $scope.data = data;
      $scope.result = [{}];
      $scope.processing = false;
      $scope.has_meters = has_meters;
      $scope.org_id = org_id;

      // Columns
      $scope.columns = columns;
      $scope.protectedColumns = _.map(_.filter(columns, {merge_protection: 'Favor Existing'}), 'name');
      var defaults = {
        headerCellFilter: 'translate',
        headerCellTemplate: 'ui-grid/seedMergeHeader',
        minWidth: 75,
        width: 150
      };
      _.map($scope.columns, function (col) {
        return _.defaults(col, defaults);
      });

      var notEmpty = function (value, key) {
        return !_.isNil(value) && value !== '' && !_.includes(['$$hashKey', '$$treeLevel'], key);
      };

      var updateResult = function () {
        var cleanedData = _.map($scope.data, function (datum) {
          return _.pickBy(datum, notEmpty);
        });
        $scope.result[0] = _.defaults.apply(null, cleanedData);

        // Handle Merge Protection columns
        _.forEach($scope.protectedColumns, function (col) {
          $scope.result[0][col] = _.last($scope.data)[col];
        });

        // Concatenate Jurisdiction Tax Lot IDs if inventory_type is property
        if ($scope.inventory_type === 'properties') {
          var jurisdiction_tax_lot_col = _.find($scope.columns, {
            column_name: 'jurisdiction_tax_lot_id',
            table_name: 'TaxLotState'
          });
          if (jurisdiction_tax_lot_col) {
            var values = [];
            _.forEach(cleanedData, function (datum) {
              values = values.concat(_.split(datum[jurisdiction_tax_lot_col.name], '; '));
            });
            var cleanedValues = _.uniq(_.without(values, undefined, null, ''));
            $scope.result[0][jurisdiction_tax_lot_col.name] = _.join(cleanedValues.sort(naturalSort), '; ');
          }
        }
      };
      updateResult();

      var determineHiddenColumns = function () {
        var visibleColumns = _.keys($scope.result[0]);
        _.forEach($scope.columns, function (col) {
          if (!_.includes(visibleColumns, col.name)) {
            col.visible = false;
          }
        });
      };
      determineHiddenColumns();

      var reverseOrder = function () {
        $scope.data.reverse();
        updateResult();
      };

      var notify_merges_and_links = function (result) {
        var singular = ($scope.inventory_type === 'properties' ? ' property' : ' tax lot');
        var plural = ($scope.inventory_type === 'properties' ? ' properties' : ' tax lots');
        // The term "subsequent" below implies not including itself
        var merged_count = Math.max(result.match_merged_count - 1, 0);
        var link_count = result.match_link_count;

        Notification.info({
          message: (merged_count + ' subsequent ' + (merged_count === 1 ? singular : plural) + ' merged'),
          delay: 10000
        });
        Notification.info({
          message: ('Resulting ' + singular + ' has ' + link_count + ' cross-cycle link' + (link_count === 1 ? '' : 's')),
          delay: 10000
        });
      };

      $scope.open_match_merge_link_warning_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/record_match_merge_link_modal.html',
          controller: 'record_match_merge_link_modal_controller',
          resolve: {
            inventory_type: function () {
              return $scope.inventory_type;
            },
            organization_id: function () {
              return $scope.org_id;
            },
            headers: function () {
              return {
                properties: 'The resulting property will be further merged & linked with any matching properties.',
                taxlots: 'The resulting tax lot will be further merged & linked with any matching tax lots.'
              };
            }
          }
        });

        modalInstance.result.then($scope.merge, function () {
          // Do nothing if cancelled
        });
      };

      $scope.merge = function () {
        $scope.processing = true;
        if ($scope.inventory_type === 'properties') {
          const property_view_ids = _.map($scope.data, 'property_view_id').reverse();
          return matching_service.mergeProperties(property_view_ids).then(function (data) {
            Notification.success('Successfully merged ' + property_view_ids.length + ' properties');
            notify_merges_and_links(data);
            $scope.close();
          }, function (err) {
            $log.error(err);
            Notification.error('Failed to merge properties');
          }).finally(function () {
            $scope.processing = false;
          });
        } else {
          const view_ids = _.map($scope.data, 'taxlot_view_id').reverse();
          return matching_service.mergeTaxlots(view_ids).then(function (data) {
            Notification.success('Successfully merged ' + view_ids.length + ' tax lots');
            notify_merges_and_links(data);
            $scope.close();
          }, function (err) {
            $log.error(err);
            Notification.error('Failed to merge tax lots');
          }).finally(function () {
            $scope.processing = false;
          });
        }
      };

      $scope.resultingGridOptions = {
        data: 'result',
        enableColumnMenus: false,
        enableGridMenu: false,
        enableSorting: false,
        enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
        flatEntityAccess: true,
        minRowsToShow: 1,
        columnDefs: $scope.columns
      };

      $scope.gridOptions = {
        data: 'data',
        enableColumnMenus: false,
        enableGridMenu: true,
        enableSorting: false,
        flatEntityAccess: true,
        gridMenuCustomItems: [{
          title: 'Reverse order',
          action: reverseOrder
        }],
        gridMenuShowHideColumns: false,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: $scope.columns,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          gridApi.draggableRows.on.rowDropped($scope, updateResult);
        }
      };
      if (data.length < 10) $scope.gridOptions.minRowsToShow = data.length;

      $scope.close = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
