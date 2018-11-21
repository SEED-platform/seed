/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_map', [])
  .controller('inventory_map_controller', [
    '$scope',
    '$filter',
    '$window',
    '$uibModal',
    '$stateParams',
    'inventory_service',
    'label_service',
    'data_quality_service',
    'user_service',
    'inventory',
    'cycles',
    'profiles',
    'current_profile',
    'labels',
    'all_columns',
    'urls',
    'spinner_utility',
    'naturalSort',
    '$translate',
    'i18nService', // from ui-grid
    function ($scope,
              $filter,
              $window,
              $uibModal,
              $stateParams,
              inventory_service,
              label_service,
              data_quality_service,
              user_service,
              inventory,
              cycles,
              profiles,
              current_profile,
              labels,
              all_columns,
              urls,
              spinner_utility,
              naturalSort,
              $translate,
              i18nService) {
      spinner_utility.show();
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;
      $scope.selectedOrder = [];

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = inventory.results;
      $scope.pagination = inventory.pagination;

      // set up i18n
      //
      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // List Settings Profile
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      if ($scope.currentProfile) {
        $scope.columns = [];
        _.forEach($scope.currentProfile.columns, function (col) {
          var foundCol = _.find(all_columns, {id: col.id});
          if (foundCol) {
            foundCol.pinnedLeft = col.pinned;
            $scope.columns.push(foundCol);
          }
        });
      } else {
        // No profiles exist
        $scope.columns = _.reject(all_columns, 'is_extra_data');
      }

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

      var ignoreNextChange = true;
      $scope.$watch('currentProfile', function (newProfile, oldProfile) {
        if (ignoreNextChange) {
          ignoreNextChange = false;
          return;
        }

        inventory_service.save_last_profile(newProfile.id, $scope.inventory_type);
        spinner_utility.show();
        $window.location.reload();
      });

      $scope.newProfile = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/settings_profile_modal.html',
          controller: 'settings_profile_modal_controller',
          resolve: {
            action: _.constant('new'),
            data: currentColumns,
            settings_location: _.constant('List View Settings'),
            inventory_type: function () {
              return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            }
          }
        });

        return modalInstance.result.then(function (newProfile) {
          $scope.profiles.push(newProfile);
          ignoreNextChange = true;
          $scope.currentProfile = _.last($scope.profiles);
          inventory_service.save_last_profile(newProfile.id, $scope.inventory_type);
        });
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

      function updateApplicableLabels() {
        var inventoryIds;
        if ($scope.inventory_type === 'properties') {
          inventoryIds = _.map($scope.data, 'property_view_id').sort();
        } else {
          inventoryIds = _.map($scope.data, 'taxlot_view_id').sort();
        }
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
            var view_id;
            if ($scope.inventory_type === 'properties') {
              view_id = row.entity.property_view_id;
            } else {
              view_id = row.entity.taxlot_view_id;
            }
            if ($scope.labelLogic === 'exclude') {
              if ((_.includes(ids, view_id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.gridApi.core.setRowInvisible(row);
              else $scope.gridApi.core.clearRowInvisible(row);
            } else {
              if ((!_.includes(ids, view_id) && row.treeLevel === 0) || !_.has(row, 'treeLevel')) $scope.gridApi.core.setRowInvisible(row);
              else $scope.gridApi.core.clearRowInvisible(row);
            }
          });
        } else {
          _.forEach($scope.gridApi.grid.rows, $scope.gridApi.core.clearRowInvisible);
        }
        // _.delay($scope.updateHeight, 150);
      };

      $scope.labelLogic = localStorage.getItem('labelLogic');
      $scope.labelLogic = _.includes(['and', 'or', 'exclude'], $scope.labelLogic) ? $scope.labelLogic : 'and';
      $scope.labelLogicUpdated = function (labelLogic) {
        $scope.labelLogic = labelLogic;
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

      $scope.open_merge_modal = function () {
        spinner_utility.show();
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/merge_modal.html',
          controller: 'merge_modal_controller',
          windowClass: 'merge-modal',
          resolve: {
            columns: function () {
              var func;
              if ($stateParams.inventory_type === 'properties') func = inventory_service.get_mappable_property_columns;
              else func = inventory_service.get_mappable_taxlot_columns;

              return func().then(function (columns) {
                return _.map(columns, function (column) {
                  return _.pick(column, ['column_name', 'displayName', 'id', 'is_extra_data', 'name', 'table_name', 'merge_protection']);
                });
              });
            },
            data: function () {
              var selectedOrder = $scope.selectedOrder.slice().reverse();
              var data = new Array($scope.selectedOrder.length);

              if ($scope.inventory_type === 'properties') {
                return inventory_service.get_properties(1, undefined, undefined, undefined, selectedOrder).then(function (inventory_data) {
                  _.forEach(selectedOrder, function (id, index) {
                    var match = _.find(inventory_data.results, {id: id});
                    if (match) {
                      data[index] = match;
                    }
                  });
                  return data;
                });
              } else if ($scope.inventory_type === 'taxlots') {
                return inventory_service.get_taxlots(1, undefined, undefined, undefined, selectedOrder).then(function (inventory_data) {
                  _.forEach(selectedOrder, function (id, index) {
                    var match = _.find(inventory_data.results, {id: id});
                    if (match) {
                      data[index] = match;
                    }
                  });
                  return data;
                });
              }
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });
        modalInstance.result.then(function () {
          // dialog was closed with 'Merge' button.
          $scope.selectedOrder = [];
          refresh_objects();
        });
      };

      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: inventory.cycle_id}),
        cycles: cycles.cycles
      };

      // Data
      var processData = function () {
        var visibleColumns = _.map($scope.columns, 'name')
          .concat(['$$treeLevel', 'notes_count', 'id', 'property_state_id', 'property_view_id', 'taxlot_state_id', 'taxlot_view_id']);

        var columnsToAggregate = _.filter($scope.columns, 'treeAggregationType').reduce(function (obj, col) {
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
            var updated = _.reduce(related[j], function (result, value, key) {
              if (_.includes(columnNamesToAggregate, key)) aggregations[key] = (aggregations[key] || []).concat(_.split(value, '; '));
              result[key] = value;
              return result;
            }, {});

            data.splice(++trueIndex, 0, _.pick(updated, visibleColumns));
          }

          aggregations = _.pickBy(_.mapValues(aggregations, function (values, key) {
            var col = findColumn(key);
            var cleanedValues = _.without(values, undefined, null, '');

            if (col.data_type === 'datetime') {
              cleanedValues = _.map(cleanedValues, function (value) {
                return $filter('date')(value, 'yyyy-MM-dd h:mm a');
              });
            }

            if (cleanedValues.length > 1) cleanedValues = _.uniq(cleanedValues);

            if (col.column_name === 'number_properties') {
              return _.sum(_.map(cleanedValues, _.toNumber)) || null;
            } else {
              if (cleanedValues.length === 1) return cleanedValues[0];
              return _.join(_.uniq(cleanedValues).sort(naturalSort), '; ');
            }
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
        spinner_utility.show();
        if ($scope.inventory_type === 'properties') {
          inventory_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, _.has($scope.currentProfile, 'id') ? $scope.currentProfile.id : undefined).then(function (properties) {
            $scope.data = properties.results;
            $scope.pagination = properties.pagination;
            processData();
            spinner_utility.hide();
          });
        } else if ($scope.inventory_type === 'taxlots') {
          inventory_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle, _.has($scope.currentProfile, 'id') ? $scope.currentProfile.id : undefined).then(function (taxlots) {
            $scope.data = taxlots.results;
            $scope.pagination = taxlots.pagination;
            processData();
            spinner_utility.hide();
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
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_state_id');
            },
            taxlot_states: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_state_id');
            }
          }
        });

        modalInstance.result.then(function (result) {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) refresh_objects();
          else if (result.delete_state === 'success') {
            var selectedRows = $scope.gridApi.selection.getSelectedRows();
            var selectedChildRows = _.remove(selectedRows, function (row) {
              return !_.has(row, '$$treeLevel');
            });
            // Delete selected child rows first
            _.forEach(selectedChildRows, function (row) {
              var index = $scope.data.lastIndexOf(row);
              var count = 1;
              if (row.$$treeLevel === 0) {
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
              if (row.$$treeLevel === 0) {
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
            if ($scope.inventory_type === 'properties') {
              _.remove($scope.data, function (row) {
                return !_.has(row, '$$treeLevel') && _.includes(result.taxlot_states, row.taxlot_state_id);
              });
            } else if ($scope.inventory_type === 'taxlots') {
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

    }]);
