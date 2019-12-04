/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_list', [])
  .controller('inventory_list_controller', [
    '$scope',
    '$filter',
    '$window',
    '$uibModal',
    '$sce',
    '$stateParams',
    'inventory_service',
    'label_service',
    'data_quality_service',
    'geocode_service',
    'user_service',
    'cycles',
    'profiles',
    'current_profile',
    'labels',
    'all_columns',
    'urls',
    'spinner_utility',
    'naturalSort',
    '$translate',
    'uiGridConstants',
    'i18nService', // from ui-grid
    function (
      $scope,
      $filter,
      $window,
      $uibModal,
      $sce,
      $stateParams,
      inventory_service,
      label_service,
      data_quality_service,
      geocode_service,
      user_service,
      cycles,
      profiles,
      current_profile,
      labels,
      all_columns,
      urls,
      spinner_utility,
      naturalSort,
      $translate,
      uiGridConstants,
      i18nService
    ) {
      spinner_utility.show();
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;
      $scope.selectedOrder = [];

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = [];
      var lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: lastCycleId ? _.find(cycles.cycles, {id: lastCycleId}) : _.first(cycles.cycles),
        cycles: cycles.cycles
      };

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
      $scope.$watch('currentProfile', function (newProfile) {
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

      $scope.open_show_populated_columns_modal = function () {
        if (!profiles.length) {
          // Create a profile first
          $scope.newProfile().then(function () {
            populated_columns_modal();
          });
        } else {
          populated_columns_modal();
        }
      };

      function populated_columns_modal() {
        $uibModal.open({
          backdrop: 'static',
          templateUrl: urls.static_url + 'seed/partials/show_populated_columns_modal.html',
          controller: 'show_populated_columns_modal_controller',
          resolve: {
            columns: function () {
              return all_columns;
            },
            currentProfile: function () {
              return $scope.currentProfile;
            },
            cycle: function () {
              return $scope.cycle.selected_cycle;
            },
            inventory_type: function () {
              return $stateParams.inventory_type;
            }
          }
        });
      }

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

      function updateApplicableLabels(current_labels) {
        var inventoryIds;
        if ($scope.inventory_type === 'properties') {
          inventoryIds = _.map($scope.data, 'property_view_id').sort();
        } else {
          inventoryIds = _.map($scope.data, 'taxlot_view_id').sort();
        }
        $scope.labels = _.filter(current_labels, function (label) {
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
        _.delay($scope.updateHeight, 150);
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
              var view_id_prop = ($scope.inventory_type === 'taxlots') ? 'taxlot_view_id' : 'property_view_id';
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), {$$treeLevel: 0}), view_id_prop);
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
                return inventory_service.get_properties(1, undefined, undefined, -1, selectedOrder).then(function (inventory_data) {
                  _.forEach(selectedOrder, function (id, index) {
                    var match = _.find(inventory_data.results, {id: id});
                    if (match) {
                      data[index] = match;
                    }
                  });
                  return data;
                });
              } else if ($scope.inventory_type === 'taxlots') {
                return inventory_service.get_taxlots(1, undefined, undefined, -1, selectedOrder).then(function (inventory_data) {
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
            },
            has_meters: function () {
              if ($scope.inventory_type === 'properties') {
                var inventory_ids = $scope.selectedOrder.slice().reverse();
                return inventory_service.properties_meters_exist(inventory_ids).then(function (has_meters) {
                  return has_meters;
                });
              } else {
                return false;
              }
            }
          }
        });
        modalInstance.result.then(function () {
          // dialog was closed with 'Merge' button.
          $scope.selectedOrder = [];
          refresh_objects();
        });
      };

      var propertyPolygonCache = {};
      var taxlotPolygonCache = {};
      var propertyFootprintColumn = _.find($scope.columns, {column_name: 'property_footprint', table_name: 'PropertyState'});
      var taxlotFootprintColumn = _.find($scope.columns, {column_name: 'taxlot_footprint', table_name: 'TaxLotState'});
      $scope.polygon = function (record, tableName) {
        var outputSize = 180;

        var cache, field;
        if (tableName === 'PropertyState') {
          cache = propertyPolygonCache;
          field = propertyFootprintColumn.name;
        } else {
          cache = taxlotPolygonCache;
          field = taxlotFootprintColumn.name;
        }

        if (!_.has(cache, record.id)) {
          var footprint;
          try {
            footprint = Terraformer.WKT.parse(record[field]);
          } catch (e) {
            return record[field];
          }
          var coords = Terraformer.toMercator(footprint).coordinates[0];
          var envelope = Terraformer.Tools.calculateEnvelope(footprint);

          // padding to allow for svg stroke
          var padding = 2;
          var scale = (outputSize - padding) / Math.max(envelope.h, envelope.w);

          var width = (envelope.w <= envelope.h) ? Math.ceil(envelope.w * scale + padding) : outputSize;
          var height = (envelope.h <= envelope.w) ? Math.ceil(envelope.h * scale + padding) : outputSize;

          var xOffset = (width - envelope.w * scale) / 2;
          var yOffset = (height - envelope.h * scale) / 2;

          var points = _.map(coords, function (coord) {
            var x = _.round((coord[0] - envelope.x) * scale + xOffset, 2);
            var y = _.round(height - ((coord[1] - envelope.y) * scale + yOffset), 2);
            return x + ',' + y;
          });

          var svg = '<svg height="' + height + '" width="' + width + '"><polygon points="' + _.initial(points).join(' ') + '" style="fill:#ffab66;stroke:#aaa;stroke-width:1;" /></svg>';

          cache[record.id] = $sce.trustAsHtml(svg);
        }
        return cache[record.id];
      };

      $scope.run_data_quality_check = function () {
        spinner_utility.show();

        var property_states = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
          return !_.has(row, '$$treeLevel');
        }), 'property_state_id');

        var taxlot_states = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
          return !_.has(row, '$$treeLevel');
        }), 'taxlot_state_id');

        data_quality_service.start_data_quality_checks(property_states, taxlot_states).then(function (response) {
          data_quality_service.data_quality_checks_status(response.progress_key).then(function (result) {
            data_quality_service.get_data_quality_results(user_service.get_organization().id, result.unique_id).then(function (dq_result) {
              var modalInstance = $uibModal.open({
                templateUrl: urls.static_url + 'seed/partials/data_quality_modal.html',
                controller: 'data_quality_modal_controller',
                size: 'lg',
                resolve: {
                  dataQualityResults: function () {
                    return dq_result;
                  },
                  name: _.constant(null),
                  uploaded: _.constant(null),
                  importFileId: _.constant(result.unique_id),
                  orgId: _.constant(user_service.get_organization().id)
                }
              });
              modalInstance.result.then(function () {
                //dialog was closed with 'Done' button.
                get_labels();
              });
            });
          }).finally(function () {
            spinner_utility.hide();
          });
        });
      };

      // Columns
      var defaults = {
        headerCellFilter: 'translate',
        minWidth: 75,
        width: 150
      };
      _.map($scope.columns, function (col) {
        var options = {};
        if (_.isMatch(col, {column_name: 'property_footprint', table_name: 'PropertyState'})) {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'PropertyState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        } else if (_.isMatch(col, {column_name: 'taxlot_footprint', table_name: 'TaxLotState'})) {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'TaxLotState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        } else {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip="{{COL_FIELD CUSTOM_FILTERS}}" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        }
        if (col.data_type === 'datetime') {
          options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
          options.filter = inventory_service.dateFilter();
        } else {
          options.filter = inventory_service.combinedFilter();
          options.sortingAlgorithm = naturalSort;
        }
        if (col.column_name === 'number_properties' && col.related) options.treeAggregationType = 'total';
        else if (col.related || col.is_extra_data) options.treeAggregationType = 'uniqueList';
        return _.defaults(col, options, defaults);
      });
      $scope.columns.unshift({
        name: 'merged_indicator',
        displayName: '',
        cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <div class="ui-grid-cell-contents merged-indicator">' +
          '    <i class="fa fa-code-fork" ng-class="{\'text-muted\': !row.entity.merged_indicator, \'text-info\': row.entity.merged_indicator}"></i>' +
          '  </div>' +
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
      }, {
        name: 'notes_count',
        displayName: '',
        cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a class="ui-grid-cell-contents notes-button" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count ? row.entity.notes_count : \'\' $}</div>' +
          '  </a>' +
          '  <a class="ui-grid-cell-contents notes-button" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id} : {inventory_type: \'properties\', view_id: row.entity.property_view_id})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count ? row.entity.notes_count : \'\' $}</div>' +
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
      }, {
        name: 'id',
        displayName: '',
        cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
          '    <i class="ui-grid-icon-info-circled"></i>' +
          '  </a>' +
          '  <a class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id} : {inventory_type: \'properties\', view_id: row.entity.property_view_id})">' +
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

      var findColumn = _.memoize(function (name) {
        return _.find(all_columns, {name: name});
      });

      // Data
      var processData = function (data) {
        if (_.isUndefined(data)) data = $scope.data;
        var visibleColumns = _.map($scope.columns, 'name')
          .concat(['$$treeLevel', 'notes_count', 'merged_indicator', 'id', 'property_state_id', 'property_view_id', 'taxlot_state_id', 'taxlot_view_id']);

        var columnsToAggregate = _.filter($scope.columns, 'treeAggregationType').reduce(function (obj, col) {
          obj[col.name] = col.treeAggregationType;
          return obj;
        }, {});
        var columnNamesToAggregate = _.keys(columnsToAggregate);

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
        get_labels();
        $scope.updateQueued = true;
      };

      var fetch = function (page, chunk) {
        // console.log('Fetching page ' + page + ' (chunk size ' + chunk + ')');
        var fn;
        if ($scope.inventory_type === 'properties') {
          fn = inventory_service.get_properties;
        } else if ($scope.inventory_type === 'taxlots') {
          fn = inventory_service.get_taxlots;
        }
        return fn(page, chunk, $scope.cycle.selected_cycle, _.get($scope, 'currentProfile.id')).then(function (data) {
          $scope.progress = {
            current: data.pagination.end,
            total: data.pagination.total,
            percent: Math.round(data.pagination.end / data.pagination.total * 100)
          };
          if (data.pagination.has_next) {
            return fetch(page + 1, chunk).then(function (data2) {
              return data.results.concat(data2);
            });
          }
          return data.results;
        });
      };

      var refresh_objects = function () {
        var page = 1;
        var chunk = 5000;
        $scope.progress = {};
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
          backdrop: 'static',
          windowClass: 'inventory-progress-modal',
          scope: $scope
        });
        // console.time('fetch');
        return fetch(page, chunk).then(function (data) {
          // console.timeEnd('fetch');
          processData(data);
          $scope.gridApi.core.notifyDataChange(uiGridConstants.dataChange.EDIT);
          modalInstance.close();
        });
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

      var get_labels = function () {
        label_service.get_labels($scope.inventory_type).then(function (current_labels) {
          updateApplicableLabels(current_labels);
        });
      };

      processData();

      $scope.open_ubid_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/ubid_modal.html',
          controller: 'ubid_modal_controller',
          resolve: {
            property_state_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_state_id');
            },
            taxlot_state_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_state_id');
            }
          }
        });
      };

      $scope.open_geocode_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/geocode_modal.html',
          controller: 'geocode_modal_controller',
          resolve: {
            property_state_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_state_id');
            },
            taxlot_state_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_state_id');
            },
            org_id: function () {
              return user_service.get_organization().id;
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });

        modalInstance.result.then(function (/*result*/) {
          // dialog was closed with 'Close' button.
          refresh_objects();
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

      $scope.open_export_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/export_inventory_modal.html',
          controller: 'export_inventory_modal_controller',
          resolve: {
            cycle_id: function () {
              return $scope.cycle.selected_cycle.id;
            },
            ids: function () {
              var visibleRowIds = _.map($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), function (row) {
                return row.entity.id;
              });
              var selectedRowIds = _.map($scope.gridApi.selection.getSelectedRows(), 'id');
              return _.filter(visibleRowIds, function (id) {
                return _.includes(selectedRowIds, id);
              });
            },
            columns: function () {
              return _.map($scope.columns, 'name');
            },
            inventory_type: function () {
              return $scope.inventory_type;
            },
            profile_id: function () {
              // Check to see if the profile id is set
              if ($scope.currentProfile) {
                return $scope.currentProfile.id;
              } else {
                return null;
              }
            }
          }
        });
      };

      function currentColumns() {
        // Save all columns except first 3
        var gridCols = _.filter($scope.gridApi.grid.columns, function (col) {
          return !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'notes_count', 'merged_indicator', 'id'], col.name) && col.visible;
        });

        // Ensure pinned ordering first
        var pinned = _.remove(gridCols, function (col) {
          return col.renderContainer === 'left';
        });
        gridCols = pinned.concat(gridCols);

        var columns = [];
        _.forEach(gridCols, function (col) {
          columns.push({
            column_name: col.colDef.column_name,
            id: col.colDef.id,
            order: columns.length + 1,
            pinned: col.renderContainer === 'left',
            table_name: col.colDef.table_name
          });
        });

        return columns;
      }

      var saveSettings = function () {
        if (!profiles.length) {
          // Create a profile first
          $scope.newProfile().then(function () {
            var id = $scope.currentProfile.id;
            var profile = _.omit($scope.currentProfile, 'id');
            profile.columns = currentColumns();
            inventory_service.update_settings_profile(id, profile);
          });
        } else {
          var id = $scope.currentProfile.id;
          var profile = _.omit($scope.currentProfile, 'id');
          profile.columns = currentColumns();
          inventory_service.update_settings_profile(id, profile);
        }
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
            // Ensure that 'merged_indicator', 'notes_count', and 'id' remain first
            var col, staticColIndex;
            staticColIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'merged_indicator'});
            if (staticColIndex !== 2) {
              col = $scope.gridApi.grid.columns[staticColIndex];
              $scope.gridApi.grid.columns.splice(staticColIndex, 1);
              $scope.gridApi.grid.columns.splice(2, 0, col);
            }
            staticColIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'notes_count'});
            if (staticColIndex !== 3) {
              col = $scope.gridApi.grid.columns[staticColIndex];
              $scope.gridApi.grid.columns.splice(staticColIndex, 1);
              $scope.gridApi.grid.columns.splice(3, 0, col);
            }
            staticColIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'id'});
            if (staticColIndex !== 4) {
              col = $scope.gridApi.grid.columns[staticColIndex];
              $scope.gridApi.grid.columns.splice(staticColIndex, 1);
              $scope.gridApi.grid.columns.splice(4, 0, col);
            }
            saveSettings();
          });
          gridApi.core.on.columnVisibilityChanged($scope, saveSettings);
          gridApi.core.on.filterChanged($scope, _.debounce(saveGridSettings, 150));
          gridApi.core.on.sortChanged($scope, _.debounce(saveGridSettings, 150));
          gridApi.pinning.on.columnPinned($scope, saveSettings);

          var selectionChanged = function () {
            var selected = gridApi.selection.getSelectedRows();
            var parentsSelectedIds = _.map(_.filter(selected, {$$treeLevel: 0}), 'id');
            $scope.selectedCount = selected.length;
            $scope.selectedParentCount = parentsSelectedIds.length;

            var removed = _.difference($scope.selectedOrder, parentsSelectedIds);
            var added = _.difference(parentsSelectedIds, $scope.selectedOrder);
            if (removed.length === 1 && !added.length) {
              // console.log('Removed ', removed);
              _.remove($scope.selectedOrder, function (item) {
                return item === removed[0];
              });
            } else if (added.length === 1 && !removed.length) {
              // console.log('Added ', added);
              $scope.selectedOrder.push(added[0]);
            }
          };

          var selectAllChanged = function () {
            var allSelected = $scope.gridApi.selection.getSelectedRows();

            if (!allSelected.length) {
              $scope.selectedCount = 0;
              $scope.selectedParentCount = 0;
              $scope.selectedOrder = [];
            } else {
              var parentsSelectedIds = _.map(_.filter(allSelected, {$$treeLevel: 0}), 'id');
              var sortedIds = _.map($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), function (row) {
                return row.entity.id;
              });
              $scope.selectedOrder = _.filter(sortedIds, function (id) {
                return _.includes(parentsSelectedIds, id);
              });
              $scope.selectedCount = allSelected.length;
              $scope.selectedParentCount = parentsSelectedIds.length;
            }
          };

          gridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, selectAllChanged);

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

          // Load the initial data
          refresh_objects();
        }
      };
    }]);
