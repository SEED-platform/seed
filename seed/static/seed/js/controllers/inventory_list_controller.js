/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_list', [])
  .controller('inventory_list_controller', [
    '$scope',
    '$window',
    '$log',
    '$uibModal',
    '$stateParams',
    'inventory_service',
    'label_service',
    'inventory',
    'cycles',
    'labels',
    'columns',
    'urls',
    function ($scope,
              $window,
              $log,
              $uibModal,
              $stateParams,
              inventory_service,
              label_service,
              inventory,
              cycles,
              labels,
              columns,
              urls) {
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.objects = inventory.results;
      $scope.pagination = inventory.pagination;
      $scope.total = $scope.pagination.total;
      $scope.number_per_page = 999999999;

      $scope.labels = labels;
      $scope.selected_labels = [];

      var localStorageKey = 'grid.' + $scope.inventory_type;

      $scope.columns = inventory_service.loadSettings(localStorageKey, angular.copy(columns));

      $scope.clear_labels = function () {
        $scope.selected_labels = [];
      };

      $scope.loadLabelsForFilter = function (query) {
        return _.filter($scope.labels, function (lbl) {
          if (_.isEmpty(query)) {
            // Empty query so return the whole list.
            return true;
          } else {
            // Only include element if it's name contains the query string.
            return _.includes(_.toLower(lbl.name), _.toLower(query));
          }
        });
      };

      var filterUsingLabels = function () {
        // Only submit the `id` of the label to the API.
        var ids = _.intersection.apply(null, _.map($scope.selected_labels, 'is_applied'));
        if ($scope.selected_labels.length) {
          _.forEach($scope.gridApi.grid.rows, function (row) {
            if ((!_.includes(ids, row.entity.id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.gridApi.core.setRowInvisible(row);
            else $scope.gridApi.core.clearRowInvisible(row);
          });
        } else {
          _.forEach($scope.gridApi.grid.rows, $scope.gridApi.core.clearRowInvisible);
        }
        _.delay($scope.updateHeight, 150);
      };

      $scope.$watchCollection('selected_labels', filterUsingLabels);

      /**
       Opens the update building labels modal.
       All further actions for labels happen with that modal and its related controller,
       including creating a new label or applying to/removing from a building.
       When the modal is closed, and refresh labels.
       */
      $scope.open_update_labels_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/update_item_labels_modal.html',
          controller: 'update_item_labels_modal_controller',
          resolve: {
            inventory_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), {$$treeLevel: 0}), 'id');
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });
        modalInstance.result.then(function () {
          //dialog was closed with 'Done' button.
          get_labels();
        });
      };


      var lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: lastCycleId ? _.find(cycles.cycles, {id: lastCycleId}) : cycles.cycles[0],
        cycles: cycles.cycles
      };

      var processData = function () {
        var visibleColumns = _.map(_.filter($scope.columns, 'visible'), 'name')
          .concat(['$$treeLevel', 'id', 'property_state_id', 'taxlot_state_id']);
        var data = angular.copy($scope.objects);
        var roots = data.length;
        for (var i = 0, trueIndex = 0; i < roots; ++i, ++trueIndex) {
          data[trueIndex].$$treeLevel = 0;
          var related = data[trueIndex].related;
          var relatedIndex = trueIndex;
          for (var j = 0; j < related.length; ++j) {
            // Rename nested keys
            var map = {};
            if ($scope.inventory_type == 'properties') {
              map = {
                city: 'tax_city',
                state: 'tax_state',
                postal_code: 'tax_postal_code'
              };
            } else if ($scope.inventory_type == 'taxlots') {
              map = {
                address_line_1: 'property_address_line_1',
                address_line_2: 'property_address_line_2',
                city: 'property_city',
                state: 'property_state',
                postal_code: 'property_postal_code'
              };
            }
            var updated = _.reduce(related[j], function (result, value, key) {
              result[map[key] || key] = value;
              return result;
            }, {});

            data.splice(++trueIndex, 0, _.pick(updated, visibleColumns));
          }
          // Remove unnecessary data
          data[relatedIndex] = _.pick(data[relatedIndex], visibleColumns);
        }
        $scope.data = data;
        $scope.updateQueued = true;
      };

      var refresh_objects = function () {
        if ($scope.inventory_type == 'properties') {
          inventory_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (properties) {
            $scope.objects = properties.results;
            $scope.pagination = properties.pagination;
            processData();
          });
        } else if ($scope.inventory_type == 'taxlots') {
          inventory_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (taxlots) {
            $scope.objects = taxlots.results;
            $scope.pagination = taxlots.pagination;
            processData();
          });
        }
      };

      $scope.update_cycle = function (cycle) {
        inventory_service.save_last_cycle(cycle.id);
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      processData();

      var get_labels = function () {
        label_service.get_labels([], {
          inventory_type: $scope.inventory_type
        }).then(function (labels) {
          $scope.labels = _.filter(labels, function (label) {
            return !_.isEmpty(label.is_applied);
          });
        });
      };

      $scope.open_delete_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/delete_modal.html',
          controller: 'delete_modal_controller',
          resolve: {
            property_states: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type == 'properties') return row.$$treeLevel == 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_state_id');
            },
            taxlot_states: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type == 'taxlots') return row.$$treeLevel == 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_state_id');
            }
          }
        });

        modalInstance.result.then(function (result) {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) refresh_objects();
          else if (result.delete_state == 'success') {
            var selectedRows = $scope.gridApi.selection.getSelectedRows();
            var selectedChildRows = _.remove(selectedRows, function (row) {
              return !_.has(row, '$$treeLevel');
            });
            // Delete selected child rows first
            _.forEach(selectedChildRows, function (row) {
              var index = $scope.data.lastIndexOf(row);
              var count = 1;
              if (row.$$treeLevel == 0) {
                // Count children to delete
                var i = index + 1;
                while (i < ($scope.data.length - 1) && !_.has($scope.data[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' child rows');
              $scope.data.splice(index, count);
            });
            // Delete parent rows and all child rows
            _.forEach(selectedRows, function (row) {
              var index = $scope.data.lastIndexOf(row);
              var count = 1;
              if (row.$$treeLevel == 0) {
                // Count children to delete
                var i = index + 1;
                while (i < ($scope.data.length - 1) && !_.has($scope.data[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' rows');
              $scope.data.splice(index, count);
            });
          }
        }, function (result) {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) refresh_objects();
        });
      };

      var defaults = {
        minWidth: 75,
        width: 150
        //type: 'string'
      };
      _.map($scope.columns, function (col) {
        var options = {};
        if (col.type == 'number') options.filter = inventory_service.numFilter();
        else options.filter = inventory_service.textFilter();
        if (col.related) options.treeAggregationType = 'uniqueList';
        return _.defaults(col, options, defaults);
      });
      $scope.columns.unshift({
        name: 'id',
        displayName: '',
        cellTemplate: '<div class="ui-grid-row-header-link">' +
        '  <a class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ng-href="#/{$grid.appScope.inventory_type == \'properties\' ? \'properties\' : \'taxlots\'$}/{$COL_FIELD$}/cycles/{$grid.appScope.cycle.selected_cycle.id$}">' +
        '    <i class="ui-grid-icon-info-circled"></i>' +
        '  </a>' +
        '  <a class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ng-href="#/{$grid.appScope.inventory_type == \'properties\' ? \'taxlots\' : \'properties\'$}/{$COL_FIELD$}/cycles/{$grid.appScope.cycle.selected_cycle.id$}">' +
        '    <i class="ui-grid-icon-info-circled"></i>' +
        '  </a>' +
        '</div>',
        enableColumnMenu: false,
        enableColumnResizing: false,
        enableFiltering: false,
        enableHiding: false,
        enableSorting: false,
        exporterSuppressExport: true,
        pinnedLeft: true,
        width: 30
      });

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls', '.inventory-list-tab-container'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };

      $scope.open_export_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/export_inventory_modal.html',
          controller: 'export_inventory_modal_controller',
          resolve: {
            gridApi: function () {
              return $scope.gridApi;
            }
          }
        });

        modalInstance.result.then(function () {
        }, function (message) {
          console.info(message);
          console.info('Modal dismissed at: ' + new Date());
        });
      };

      var saveSettings = function () {
        // Save all columns except first 3
        var cols = _.filter($scope.gridApi.grid.columns, function (col) {
          return !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'id'], col.name);
        });
        _.map(cols, function (col) {
          col.pinnedLeft = col.renderContainer == 'left' && col.visible;
          return col;
        });
        inventory_service.saveSettings(localStorageKey, cols);
      };

      $scope.gridOptions = {
        data: 'data',
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: true,
        exporterCsvFilename: window.BE.initial_org_name + ($scope.inventory_type == 'taxlots' ? ' Tax Lot ' : ' Property ') + 'Data.csv',
        exporterMenuPdf: false,
        fastWatch: true,
        flatEntityAccess: true,
        gridMenuShowHideColumns: false,
        showTreeExpandNoChildren: false,
        columnDefs: $scope.columns,
        treeCustomAggregations: inventory_service.aggregations(),
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });

          gridApi.colMovable.on.columnPositionChanged($scope, saveSettings);
          gridApi.core.on.columnVisibilityChanged($scope, saveSettings);
          gridApi.pinning.on.columnPinned($scope, saveSettings);

          var selectionChanged = function () {
            var selected = gridApi.selection.getSelectedRows();
            $scope.selectedCount = selected.length;
            $scope.selectedParentCount = _.filter(selected, {$$treeLevel: 0}).length;
          };

          gridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, selectionChanged);

          gridApi.core.on.rowsRendered($scope, _.debounce(function () {
            $scope.$apply(function () {
              $scope.total = _.filter($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), {treeLevel: 0}).length;
              if ($scope.updateQueued) {
                $scope.updateQueued = false;
                if ($scope.selected_labels.length) filterUsingLabels();
              }
            });
          }, 150));
        }
      };

      // $scope.$on('$destroy', function () {
      //   console.log('Destroying!');
      // });
    }]);
