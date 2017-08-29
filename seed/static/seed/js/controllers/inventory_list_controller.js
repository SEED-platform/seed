/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_list', [])
  .controller('inventory_list_controller', [
    '$scope',
    '$window',
    '$uibModal',
    '$stateParams',
    'inventory_service',
    'label_service',
    'data_quality_service',
    'inventory',
    'cycles',
    'labels',
    'all_columns',
    'urls',
    'spinner_utility',
    'naturalSort',
    function ($scope,
              $window,
              $uibModal,
              $stateParams,
              inventory_service,
              label_service,
              data_quality_service,
              inventory,
              cycles,
              labels,
              all_columns,
              urls,
              spinner_utility,
              naturalSort) {
      spinner_utility.show();
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = inventory.results;
      $scope.pagination = inventory.pagination;
      $scope.columns = _.filter(inventory.columns, 'visible');
      $scope.total = $scope.pagination.total;
      $scope.number_per_page = 999999999;
      $scope.restoring = false;

      // Reduce labels to only records found in the current cycle
      $scope.selected_labels = [];
      updateApplicableLabels();

      var localStorageKey = 'grid.' + $scope.inventory_type;
      var localStorageLabelKey = 'grid.' + $scope.inventory_type + '.labels';

      // Reapply valid previously-applied labels
      var ids = inventory_service.loadSelectedLabels(localStorageLabelKey);
      $scope.selected_labels = _.filter($scope.labels, function (label) {
        return _.includes(ids, label.id);
      });

      $scope.clear_labels = function () {
        $scope.selected_labels = [];
      };

      $scope.loadLabelsForFilter = function (query) {
        return _.filter($scope.labels, function (lbl) {
          if (_.isEmpty(query)) {
            // Empty query so return the whole list.
            return true;
          } else {
            // Only include element if its name contains the query string.
            return _.includes(_.toLower(lbl.name), _.toLower(query));
          }
        });
      };

      function updateApplicableLabels () {
        var inventoryIds = _.map($scope.data, 'id').sort();
        $scope.labels = _.filter(labels, function (label) {
          return _.some(label.is_applied, function (id) {
            return _.includes(inventoryIds, id);
          });
        });
        // Ensure that no previously-applied labels remain
        var new_labels = _.filter($scope.selected_labels, function (label) {
          return _.includes($scope.labels, label.id);
        });
        if ($scope.selected_labels.length !== new_labels.length) {
          $scope.selected_labels = new_labels;
        }
      }

      var filterUsingLabels = function () {
        // Only submit the `id` of the label to the API.
        var ids;
        if ($scope.labelLogic === 'and') {
          ids = _.intersection.apply(null, _.map($scope.selected_labels, 'is_applied'));
        } else if (_.includes(['or', 'exclude'], $scope.labelLogic)) {
          ids = _.union.apply(null, _.map($scope.selected_labels, 'is_applied'));
        }

        inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_labels, 'id'));

        if ($scope.selected_labels.length) {
          _.forEach($scope.gridApi.grid.rows, function (row) {
            if ($scope.labelLogic === 'exclude') {
              if ((_.includes(ids, row.entity.id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.gridApi.core.setRowInvisible(row);
              else $scope.gridApi.core.clearRowInvisible(row);
            } else {
              if ((!_.includes(ids, row.entity.id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.gridApi.core.setRowInvisible(row);
              else $scope.gridApi.core.clearRowInvisible(row);
            }
          });
        } else {
          _.forEach($scope.gridApi.grid.rows, $scope.gridApi.core.clearRowInvisible);
        }
        _.delay($scope.updateHeight, 150);
      };

      $scope.labelLogic = localStorage.getItem('labelLogic');
      $scope.labelLogic = _.includes(['and', 'or', 'exclude'], $scope.labelLogic) ? $scope.labelLogic : 'and';
      $scope.labelLogicUpdated = function () {
        localStorage.setItem('labelLogic', $scope.labelLogic);
        filterUsingLabels();
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

      $scope.run_data_quality_check = function () {
        spinner_utility.show();

        var property_states = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'properties') return row.$$treeLevel == 0;
          return !_.has(row, '$$treeLevel');
        }), 'property_state_id');

        var taxlot_states = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'taxlots') return row.$$treeLevel == 0;
          return !_.has(row, '$$treeLevel');
        }), 'taxlot_state_id');

        data_quality_service.start_data_quality_checks(property_states, taxlot_states).then(function (response) {
          data_quality_service.data_quality_checks_status(response.progress_key).then(function (result) {
            var modalInstance = $uibModal.open({
              templateUrl: urls.static_url + 'seed/partials/data_quality_modal.html',
              controller: 'data_quality_modal_controller',
              size: 'lg',
              resolve: {
                dataQualityResults: function () {
                  return result;
                },
                name: _.constant(null),
                uploaded: _.constant(null),
                importFileId: _.constant(null)
              }
            });
            modalInstance.result.then(function () {
              //dialog was closed with 'Done' button.
              get_labels();
            });
          }).finally(function () {
            spinner_utility.hide();
          });
        });
      };

      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: inventory.cycle_id}),
        cycles: cycles.cycles
      };

      // Columns
      var defaults = {
        minWidth: 75,
        width: 150
        //type: 'string'
      };
      _.map($scope.columns, function (col) {
        var options = {};
        if (col.type === 'number') options.filter = inventory_service.numFilter();
        else if (col.type === 'date') options.filter = inventory_service.dateFilter();
        else options.filter = inventory_service.textFilter();
        if (col.type === 'text' || _.isUndefined(col.type)) options.sortingAlgorithm = naturalSort;
        if (col.name === 'number_properties' && col.related) options.treeAggregationType = 'total';
        else if (col.related || col.extraData) options.treeAggregationType = 'uniqueList';
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
        enableColumnMoving: false,
        enableColumnResizing: false,
        enableFiltering: false,
        enableHiding: false,
        enableSorting: false,
        exporterSuppressExport: true,
        pinnedLeft: true,
        visible: true,
        width: 30
      });

      // Data
      var processData = function () {
        var visibleColumns = _.map(_.filter($scope.columns, 'visible'), 'name')
          .concat(['$$treeLevel', 'id', 'property_state_id', 'taxlot_state_id']);

        var columnsToAggregate = _.filter($scope.columns, function (col) {
          return col.treeAggregationType && _.includes(visibleColumns, col.name);
        }).reduce(function (obj, col) {
          obj[col.name] = col.treeAggregationType;
          return obj;
        }, {});
        var columnNamesToAggregate = _.keys(columnsToAggregate);

        var data = $scope.data;
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
            else return _.join(_.uniq(cleanedValues).sort(naturalSort), '; ');
          }), function (result) {
            return _.isNumber(result) || !_.isEmpty(result);
          });

          // Remove unnecessary data
          data[relatedIndex] = _.pick(data[relatedIndex], visibleColumns);
          // Insert aggregated child values into parent row
          _.merge(data[relatedIndex], aggregations);
        }
        $scope.data = data;
        updateApplicableLabels();
        $scope.updateQueued = true;
      };

      var refresh_objects = function () {
        var visibleColumns = _.map(_.filter($scope.columns, 'visible'), 'name');
        if ($scope.inventory_type == 'properties') {
          inventory_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, visibleColumns).then(function (properties) {
            $scope.data = properties.results;
            $scope.pagination = properties.pagination;
            processData();
          });
        } else if ($scope.inventory_type == 'taxlots') {
          inventory_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, visibleColumns).then(function (taxlots) {
            $scope.data = taxlots.results;
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

      $scope.filters_exist = function () {
        return !!_.find($scope.gridApi.grid.columns, function (col) {
          return !_.isEmpty(col.filter.term);
        });
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
            // Delete any child rows that may have been duplicated due to a M2M relationship
            if ($scope.inventory_type == 'properties') {
              _.remove($scope.data, function (row) {
                return !_.has(row, '$$treeLevel') && _.includes(result.taxlot_states, row.taxlot_state_id);
              });
            } else if ($scope.inventory_type == 'taxlots') {
              _.remove($scope.data, function (row) {
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
        $scope.gridApi.core.handleWindowResize();
      };

      $scope.open_export_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/export_inventory_modal.html',
          controller: 'export_inventory_modal_controller',
          resolve: {
            gridApi: function () {
              return $scope.gridApi;
            }
          }
        });
      };

      var saveSettings = function () {
        // Save all columns except first 3
        var cols = _.filter($scope.gridApi.grid.columns, function (col) {
          return !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'id'], col.name);
        });
        cols = _.map(cols, function (col) {
          col.pinnedLeft = col.renderContainer === 'left' && col.visible;
          var result = col.colDef;
          result.pinnedLeft = col.pinnedLeft;
          return result;
        });
        var oldSettings = inventory_service.loadSettings(localStorageKey, angular.copy(all_columns));
        oldSettings = _.map(oldSettings, function (col) {
          col.pinnedLeft = false;
          col.visible = false;
          return col;
        });
        var visibleColumns = _.map(cols, 'name');
        oldSettings = _.filter(oldSettings, function (col) {
          return !_.includes(visibleColumns, col.name);
        });

        inventory_service.saveSettings(localStorageKey, cols.concat(oldSettings));
      };

      var saveGridSettings = function () {
        if (!$scope.restoring) {
          var columns = _.filter($scope.gridApi.saveState.save().columns, function (col) {
            return _.keys(col.sort).length + (_.get(col, 'filters[0].term', '') || '').length > 0;
          });
          inventory_service.saveGridSettings(localStorageKey + '.sort', {
            columns: columns
          });
        }
      };

      var restoreGridSettings = function () {
        $scope.restoring = true;
        var state = inventory_service.loadGridSettings(localStorageKey + '.sort');
        if (!_.isNull(state)) {
          state = JSON.parse(state);
          $scope.gridApi.saveState.restore($scope, state);
        }
        _.defer(function () {
          $scope.restoring = false;
        });
      };

      $scope.gridOptions = {
        data: 'data',
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: true,
        exporterCsvFilename: window.BE.initial_org_name + ($scope.inventory_type === 'taxlots' ? ' Tax Lot ' : ' Property ') + 'Data.csv',
        exporterMenuPdf: false,
        fastWatch: true,
        flatEntityAccess: true,
        gridMenuShowHideColumns: false,
        showTreeExpandNoChildren: false,
        saveFocus: false,
        saveGrouping: false,
        saveGroupingExpandedStates: false,
        saveOrder: false,
        savePinning: false,
        saveScroll: false,
        saveSelection: false,
        saveTreeView: false,
        saveVisible: false,
        saveWidths: false,
        columnDefs: $scope.columns,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });

          gridApi.colMovable.on.columnPositionChanged($scope, function () {
            // Ensure that 'id' remains first
            var idIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'id'});
            if (idIndex !== 2) {
              var col = $scope.gridApi.grid.columns[idIndex];
              $scope.gridApi.grid.columns.splice(idIndex, 1);
              $scope.gridApi.grid.columns.splice(2, 0, col);
            }
            saveSettings();
          });
          gridApi.core.on.columnVisibilityChanged($scope, saveSettings);
          gridApi.core.on.filterChanged($scope, _.debounce(saveGridSettings, 150));
          gridApi.core.on.sortChanged($scope, _.debounce(saveGridSettings, 150));
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
              spinner_utility.hide();
              $scope.total = _.filter($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), {treeLevel: 0}).length;
              if ($scope.updateQueued) {
                $scope.updateQueued = false;
                if ($scope.selected_labels.length) filterUsingLabels();
              }
            });
          }, 150));

          _.defer(function () {
            restoreGridSettings();
          });
        }
      };

      // $scope.$on('$destroy', function () {
      //   console.log('Destroying!');
      // });
    }]);
