/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.pairing', [])
  .controller('pairing_controller', [
    '$scope',
    '$window',
    '$uibModal',
    '$stateParams',
    'inventory_service',
    'label_service',
    'propertyInventory',
    'taxlotInventory',
    'cycles',
    // 'columns',
    'urls',
    'spinner_utility',
    'naturalSort',
    function ($scope,
              $window,
              $uibModal,
              $stateParams,
              inventory_service,
              label_service,
              propertyInventory,
              taxlotInventory,
              cycles,
              // columns,
              urls,
              spinner_utility,
              naturalSort) {
      spinner_utility.show();
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.leftData = propertyInventory.results;
      $scope.rightData = taxlotInventory.results;
      $scope.leftColumns = propertyInventory.columns;
      $scope.rightColumns = taxlotInventory.columns;

      $scope.pagination = propertyInventory.pagination;
      $scope.total = $scope.pagination.total;
      $scope.number_per_page = 5;

      $scope.labels = [];
      $scope.selected_labels = [];

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
          _.forEach($scope.leftGridApi.grid.rows, function (row) {
            if ((!_.includes(ids, row.entity.id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.leftGridApi.core.setRowInvisible(row);
            else $scope.leftGridApi.core.clearRowInvisible(row);
          });
        } else {
          _.forEach($scope.leftGridApi.grid.rows, $scope.leftGridApi.core.clearRowInvisible);
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
              return _.map(_.filter($scope.leftGridApi.selection.getSelectedRows(), {$$treeLevel: 0}), 'id');
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
        selected_cycle: lastCycleId ? _.find(cycles.cycles, {id: lastCycleId}) : _.first(cycles.cycles),
        cycles: cycles.cycles
      };

      // Columns
      var defaults = {
        minWidth: 75,
        width: 150
        //type: 'string'
      };


      // Data
      var processData = function () {
        var visibleColumns = _.map(_.filter($scope.leftColumns, 'visible'), 'name')
          .concat(['$$treeLevel', 'id', 'property_state_id', 'taxlot_state_id']);

        var columnsToAggregate = _.filter($scope.leftColumns, function (col) {
          return col.treeAggregationType && _.includes(visibleColumns, col.name);
        }).reduce(function (obj, col) {
          obj[col.name] = col.treeAggregationType;
          return obj;
        }, {});
        var columnNamesToAggregate = _.keys(columnsToAggregate);

        var data = $scope.leftData;
        var roots = data.length;
        for (var i = 0, trueIndex = 0; i < roots; ++i, ++trueIndex) {
          data[trueIndex].$$treeLevel = 0;
          var related = data[trueIndex].related;
          var relatedIndex = trueIndex;
          var aggregations = {};
          for (var j = 0; j < related.length; ++j) {
            // Rename nested keys
            var map = {};
            if ($scope.inventory_type == 'properties') {
              map = {
                address_line_1: 'tax_address_line_1',
                address_line_2: 'tax_address_line_2',
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
              key = map[key] || key;
              if (_.includes(columnNamesToAggregate, key)) aggregations[key] = (aggregations[key] || []).concat(_.split(value, '; '));
              result[key] = value;
              return result;
            }, {});

            data.splice(++trueIndex, 0, _.pick(updated, visibleColumns));
          }

          aggregations = _.pickBy(_.mapValues(aggregations, function (values, key) {
            var cleanedValues = _.uniq(_.without(values, undefined, null, ''));
            if (key == 'number_properties') return _.sum(cleanedValues) || null;
            else return _.join(_.uniq(cleanedValues), '; ');
          }), function (result) {
            return _.isNumber(result) || !_.isEmpty(result);
          });

          // Remove unnecessary data
          data[relatedIndex] = _.pick(data[relatedIndex], visibleColumns);
          // Insert aggregated child values into parent row
          _.merge(data[relatedIndex], aggregations);
        }
        $scope.leftData = data;
        $scope.updateQueued = true;
      };

      var refresh_objects = function () {
        var visibleColumns = _.map(_.filter($scope.leftColumns, 'visible'), 'name');
        if ($scope.inventory_type == 'properties') {
          inventory_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, visibleColumns).then(function (properties) {
            $scope.leftData = properties.results;
            $scope.pagination = properties.pagination;
            processData();
          });
        } else if ($scope.inventory_type == 'taxlots') {
          inventory_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, visibleColumns).then(function (taxlots) {
            $scope.leftData = taxlots.results;
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
              return _.map(_.filter($scope.leftGridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type == 'properties') return row.$$treeLevel == 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_state_id');
            },
            taxlot_states: function () {
              return _.map(_.filter($scope.leftGridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type == 'taxlots') return row.$$treeLevel == 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_state_id');
            }
          }
        });

        modalInstance.result.then(function (result) {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) refresh_objects();
          else if (result.delete_state == 'success') {
            var selectedRows = $scope.leftGridApi.selection.getSelectedRows();
            var selectedChildRows = _.remove(selectedRows, function (row) {
              return !_.has(row, '$$treeLevel');
            });
            // Delete selected child rows first
            _.forEach(selectedChildRows, function (row) {
              var index = $scope.leftData.lastIndexOf(row);
              var count = 1;
              if (row.$$treeLevel == 0) {
                // Count children to delete
                var i = index + 1;
                while (i < ($scope.leftData.length - 1) && !_.has($scope.leftData[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' child rows');
              $scope.leftData.splice(index, count);
            });
            // Delete parent rows and all child rows
            _.forEach(selectedRows, function (row) {
              var index = $scope.leftData.lastIndexOf(row);
              var count = 1;
              if (row.$$treeLevel == 0) {
                // Count children to delete
                var i = index + 1;
                while (i < ($scope.leftData.length - 1) && !_.has($scope.leftData[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' rows');
              $scope.leftData.splice(index, count);
            });
            // Delete any child rows that may have been duplicated due to a M2M relationship
            if ($scope.inventory_type == 'properties') {
              _.remove($scope.leftData, function (row) {
                return !_.has(row, '$$treeLevel') && _.includes(result.taxlot_states, row.taxlot_state_id);
              });
            } else if ($scope.inventory_type == 'taxlots') {
              _.remove($scope.leftData, function (row) {
                return !_.has(row, '$$treeLevel') && _.includes(result.property_states, row.property_state_id);
              });
            }
          }
        }, function (result) {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) refresh_objects();
        });
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls', '.inventory-list-tab-container'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.leftGridApi.core.handleWindowResize();
      };

      $scope.open_export_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/export_inventory_modal.html',
          controller: 'export_inventory_modal_controller',
          resolve: {
            leftGridApi: function () {
              return $scope.leftGridApi;
            }
          }
        });

        // modalInstance.result.then(function () {
        // }, function (message) {
        //   console.info(message);
        //   console.info('Modal dismissed at: ' + new Date());
        // });
      };

      var saveSettings = function () {
        // Save all columns except first 3
        var cols = _.filter($scope.leftGridApi.grid.columns, function (col) {
          return !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'id'], col.name);
        });
        _.map(cols, function (col) {
          col.pinnedLeft = col.renderContainer == 'left' && col.visible;
          return col;
        });
        inventory_service.saveSettings(localStorageKey, cols);
      };

      $scope.gridOptionsLeft = {
        data: 'leftData',
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: true,
        exporterMenuPdf: false,
        fastWatch: true,
        flatEntityAccess: true,
        gridMenuShowHideColumns: false,
        showTreeExpandNoChildren: false,
        columnDefs: $scope.leftColumns,
        onRegisterApi: function (leftGridApi) {
          $scope.leftGridApi = leftGridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });

          leftGridApi.colMovable.on.columnPositionChanged($scope, saveSettings);
          leftGridApi.core.on.columnVisibilityChanged($scope, saveSettings);
          leftGridApi.pinning.on.columnPinned($scope, saveSettings);

          var selectionChanged = function () {
            var selected = leftGridApi.selection.getSelectedRows();
            $scope.selectedCount = selected.length;
            $scope.selectedParentCount = _.filter(selected, {$$treeLevel: 0}).length;
          };

          leftGridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
          leftGridApi.selection.on.rowSelectionChangedBatch($scope, selectionChanged);

          leftGridApi.core.on.rowsRendered($scope, _.debounce(function () {
            $scope.$apply(function () {
              spinner_utility.hide();
              $scope.total = _.filter($scope.leftGridApi.core.getVisibleRows($scope.leftGridApi.grid), {treeLevel: 0}).length;
              if ($scope.updateQueued) {
                $scope.updateQueued = false;
                if ($scope.selected_labels.length) filterUsingLabels();
              }
            });
          }, 150));
        }
      };

      $scope.gridOptionsRight = {
        data: 'rightData',
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: true,
        exporterMenuPdf: false,
        fastWatch: true,
        flatEntityAccess: true,
        gridMenuShowHideColumns: false,
        showTreeExpandNoChildren: false,
        columnDefs: $scope.rightColumns,
        onRegisterApi: function (rightGridApi) {
          $scope.rightGridApi = rightGridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });

          rightGridApi.colMovable.on.columnPositionChanged($scope, saveSettings);
          rightGridApi.core.on.columnVisibilityChanged($scope, saveSettings);
          rightGridApi.pinning.on.columnPinned($scope, saveSettings);

          var selectionChanged = function () {
            var selected = rightGridApi.selection.getSelectedRows();
            $scope.selectedCount = selected.length;
            $scope.selectedParentCount = _.filter(selected, {$$treeLevel: 0}).length;
          };

          rightGridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
          rightGridApi.selection.on.rowSelectionChangedBatch($scope, selectionChanged);

          rightGridApi.core.on.rowsRendered($scope, _.debounce(function () {
            $scope.$apply(function () {
              spinner_utility.hide();
              $scope.total = _.filter($scope.rightGridApi.core.getVisibleRows($scope.rightGridApi.grid), {treeLevel: 0}).length;
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
