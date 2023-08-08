/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_list_legacy', [])
  .controller('inventory_list_legacy_controller', [
    '$scope',
    '$filter',
    '$window',
    '$uibModal',
    '$sce',
    '$state',
    '$stateParams',
    '$q',
    'inventory_service',
    'label_service',
    'data_quality_service',
    'geocode_service',
    'user_service',
    'derived_columns_service',
    'Notification',
    'cycles',
    'profiles',
    'current_profile',
    'labels',
    'all_columns',
    'derived_columns_payload',
    'urls',
    'spinner_utility',
    'naturalSort',
    '$translate',
    'uiGridConstants',
    'i18nService', // from ui-grid
    'organization_payload',
    'gridUtil',
    'uiGridGridMenuService',
    function (
      $scope,
      $filter,
      $window,
      $uibModal,
      $sce,
      $state,
      $stateParams,
      $q,
      inventory_service,
      label_service,
      data_quality_service,
      geocode_service,
      user_service,
      derived_columns_service,
      Notification,
      cycles,
      profiles,
      current_profile,
      labels,
      all_columns,
      derived_columns_payload,
      urls,
      spinner_utility,
      naturalSort,
      $translate,
      uiGridConstants,
      i18nService,
      organization_payload,
      gridUtil,
      uiGridGridMenuService
    ) {
      spinner_utility.show();
      $scope.selectedCount = 0;
      $scope.selectedParentCount = 0;
      $scope.selectedOrder = [];

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = [];
      var lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: lastCycleId}) || _.first(cycles.cycles),
        cycles: cycles.cycles
      };
      $scope.organization = organization_payload.organization;

      // set up i18n
      //
      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // Column List Profile
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      if ($scope.currentProfile) {
        $scope.columns = [];
        // add columns
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

      // Find labels that should be displayed and organize by applied inventory id
      $scope.show_labels_by_inventory_id = {};
      $scope.build_labels = function () {
        $scope.show_labels_by_inventory_id = {};
        for (let n in $scope.labels) {
          let label = $scope.labels[n];
          if (label.show_in_list) {
            for (let m in label.is_applied) {
              let id = label.is_applied[m];
              if (!$scope.show_labels_by_inventory_id[id]) {
                $scope.show_labels_by_inventory_id[id] = [];
              }
              $scope.show_labels_by_inventory_id[id].push(label);
            }
          }
        }
      };
      $scope.build_labels();

      // Builds the html to display labels associated with this row entity
      $scope.display_labels = function (entity) {
        let id = $scope.inventory_type === 'properties' ? entity.property_view_id : entity.taxlot_view_id;
        let labels = [];
        let titles = [];
        if ($scope.show_labels_by_inventory_id[id]) {
          for (let i in $scope.show_labels_by_inventory_id[id]) {
            let label = $scope.show_labels_by_inventory_id[id][i];
            labels.push('<span class="', $scope.show_full_labels ? 'label' : 'label-bar', ' label-', label.label, '">', $scope.show_full_labels ? label.text : '', '</span>');
            titles.push(label.text);
          }
        }
        return ['<span title="', titles.join(', '), '" class="label-bars" style="overflow-x:scroll">', labels.join(''), '</span>'].join('');
      };

      $scope.show_full_labels = false;
      $scope.toggle_labels = function () {
        $scope.show_full_labels = !$scope.show_full_labels;
        setTimeout(() => {
          $scope.gridApi.grid.getColumn('labels').width = $scope.get_label_column_width();
          let icon = document.getElementById('label-header-icon');
          icon.classList.add($scope.show_full_labels ? 'fa-chevron-circle-left' : 'fa-chevron-circle-right');
          icon.classList.remove($scope.show_full_labels ? 'fa-chevron-circle-right' : 'fa-chevron-circle-left');
          $scope.gridApi.grid.refresh();
        }, 0);
      };

      $scope.max_label_width = 750;
      $scope.get_label_column_width = function () {
        if (!$scope.show_full_labels) {
          return 30;
        }
        let maxWidth = 0;
        let renderContainer = document.body.getElementsByClassName('ui-grid-render-container-left')[0];
        let col = $scope.gridApi.grid.getColumn('labels');
        let cells = renderContainer.querySelectorAll('.' + uiGridConstants.COL_CLASS_PREFIX + col.uid + ' .ui-grid-cell-contents');
        Array.prototype.forEach.call(cells, function (cell) {
          gridUtil.fakeElement(cell, {}, function (newElm) {
            var e = angular.element(newElm);
            e.attr('style', 'float: left;');
            var width = gridUtil.elementWidth(e);
            if (width > maxWidth) {
              maxWidth = width;
            }
          });
        });
        return maxWidth > $scope.max_label_width ? $scope.max_label_width : maxWidth + 2;
      };

      // Reduce labels to only records found in the current cycle
      $scope.selected_labels = [];

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
            data: function () {
              return {
                columns: currentColumns(),
                derived_columns: []
              };
            },
            profile_location: _.constant('List View Profile'),
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

      function populated_columns_modal () {
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
            },
            provided_inventory: _.constant(null)
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

      function updateApplicableLabels (current_labels) {
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
        // Filter on $scope.labels to refresh is_applied
        $scope.selected_labels = _.filter($scope.labels, function (label) {
          return _.find($scope.selected_labels, ['id', label.id]);
        });
        $scope.build_labels();
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

      /**
       Opens the postoffice modal for sending emails.
       'property_state_id's/'taxlot_state_id's for selected rows are stored as part of the resolver
      */
      $scope.open_postoffice_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/postoffice_modal.html',
          controller: 'postoffice_modal_controller',
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
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
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
              const viewIdProp = $scope.inventory_type === 'properties' ? 'property_view_id' : 'taxlot_view_id';
              const selectedViewIds = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                return row.$$treeLevel === 0;
              }), viewIdProp).reverse();
              var data = new Array(selectedViewIds.length);

              if ($scope.inventory_type === 'properties') {
                return inventory_service.get_properties(1, undefined, undefined, -1, selectedViewIds).then(function (inventory_data) {
                  _.forEach(selectedViewIds, function (id, index) {
                    var match = _.find(inventory_data.results, [viewIdProp, id]);
                    if (match) {
                      data[index] = match;
                    }
                  });
                  return data;
                });
              } else if ($scope.inventory_type === 'taxlots') {
                return inventory_service.get_taxlots(1, undefined, undefined, -1, selectedViewIds).then(function (inventory_data) {
                  _.forEach(selectedViewIds, function (id, index) {
                    var match = _.find(inventory_data.results, [viewIdProp, id]);
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
                const selected_property_view_ids = _.map(
                  _.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                    return row.$$treeLevel === 0;
                  }),
                  'property_view_id'
                ).reverse();

                return inventory_service.properties_meters_exist(
                  selected_property_view_ids
                ).then(function (has_meters) {
                  return has_meters;
                });
              } else {
                return false;
              }
            },
            org_id: function () {
              return $scope.organization.id;
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

        var property_view_ids = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
          return !_.has(row, '$$treeLevel');
        }), 'property_view_id');

        var taxlot_view_ids = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
          if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
          return !_.has(row, '$$treeLevel');
        }), 'taxlot_view_id');

        data_quality_service.start_data_quality_checks(property_view_ids, taxlot_view_ids).then(function (response) {
          data_quality_service.data_quality_checks_status(response.progress_key).then(function (result) {
            data_quality_service.get_data_quality_results($scope.organization.id, result.unique_id).then(function (dq_result) {
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
                  run_id: _.constant(result.unique_id),
                  orgId: _.constant($scope.organization.id)
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
        headerCellTemplate: `<div role="columnheader" ng-class="{ 'sortable': sortable, 'ui-grid-header-cell-last-col': isLastCol }" ui-grid-one-bind-aria-labelledby-grid="col.uid + '-header-text ' + col.uid + '-sortdir-text'" aria-sort="{{col.sort.direction == asc ? 'ascending' : ( col.sort.direction == desc ? 'descending' : (!col.sort.direction ? 'none' : 'other'))}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex" uib-tooltip="{{ col.colDef.column_description }}" tooltip-append-to-body="true"><span class="ui-grid-header-cell-label" ui-grid-one-bind-id-grid="col.uid + '-header-text'">{{ col.displayName CUSTOM_FILTERS }}</span> <span ui-grid-one-bind-id-grid="col.uid + '-sortdir-text'" ui-grid-visible="col.sort.direction" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ 'ui-grid-icon-up-dir': col.sort.direction == asc, 'ui-grid-icon-down-dir': col.sort.direction == desc, 'ui-grid-icon-blank': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + ' ' + ( col.sort.priority + 1 )  : null}}" aria-hidden="true"></i> <sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div><div role="button" tabindex="0" ui-grid-one-bind-id-grid="col.uid + '-menu-button'" class="ui-grid-column-menu-button" ng-if="grid.options.enableColumnMenus && !col.isRowHeader  && col.colDef.enableColumnMenu !== false" ng-click="toggleMenu($event)" ng-keydown="headerCellArrowKeyDown($event)" ui-grid-one-bind-aria-label="i18n.headerCell.aria.columnMenuButtonLabel" aria-expanded="{{col.menuShown}}" aria-haspopup="true"><i class="ui-grid-icon-angle-down" aria-hidden="true">&nbsp;</i></div><div ui-grid-filter ng-hide="col.filterContainer === 'columnMenu'"></div></div>`,
        minWidth: 75,
        width: 150
      };
      _.map($scope.columns, function (col) {
        var options = {};
        // Modify cellTemplate
        if (_.isMatch(col, {column_name: 'property_footprint', table_name: 'PropertyState'})) {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'PropertyState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        } else if (_.isMatch(col, {column_name: 'taxlot_footprint', table_name: 'TaxLotState'})) {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'TaxLotState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        } else {
          col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip="{{COL_FIELD CUSTOM_FILTERS}}" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
        }

        // Modify headerCellClass
        if (col.derived_column) {
          col.headerCellClass = 'derived-column-display-name';
        }

        // Modify misc
        if (col.data_type === 'datetime') {
          options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
          options.filter = inventory_service.dateFilter();
        } else if (col.data_type === 'date') {
          options.filter = inventory_service.dateFilter();
        } else if (['area', 'eui', 'float', 'number'].includes(col.data_type)) {
          options.filter = inventory_service.combinedFilter();
          options.cellFilter = 'number: ' + $scope.organization.display_decimal_places;
          options.sortingAlgorithm = naturalSort;
        } else if (col.is_derived_column) {
          options.filter = inventory_service.combinedFilter();
          options.cellFilter = 'number: ' + $scope.organization.display_decimal_places;
          options.sortingAlgorithm = naturalSort;
        } else {
          options.filter = inventory_service.combinedFilter();
          options.sortingAlgorithm = naturalSort;
        }

        if (col.column_name === 'number_properties' && col.related) options.treeAggregationType = 'total';
        else if (col.related || col.is_extra_data) options.treeAggregationType = 'uniqueList';
        return _.defaults(col, options, defaults);
      });
      if ($stateParams.inventory_type == 'properties') {
        $scope.columns.unshift({
          name: 'merged_indicator',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <div title="' + $translate.instant('Merged Records') + '" class="ui-grid-cell-contents merged-indicator">' +
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
          headerCellTemplate: '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a title="' + $translate.instant('Go to Notes') + '" class="ui-grid-cell-contents notes-button" ng-if="row.entity.$$treeLevel === 0" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id, record: row.entity} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id, record: row.entity})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count || \'\' $}</div>' +
          '  </a>' +
          '  <a title="' + $translate.instant('Go to Notes') + '" class="ui-grid-cell-contents notes-button" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id, record: row.entity} : {inventory_type: \'properties\', view_id: row.entity.property_view_id, record: row.entity})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count || \'\' $}</div>' +
          '  </a>' +
          '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        }, {
          name: 'meters_exist_indicator',
          displayName: '',
          headerCellTemplate: '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate: '<div class="ui-grid-row-header-link">' +
        '  <a title="' + $translate.instant('Go to Meters') + '" class="ui-grid-cell-contents meters-exist-indicator" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail_meters(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
        '    <i class="fa fa-bolt" ng-class="{\'text-muted\': !row.entity.meters_exist_indicator, \'text-info\': row.entity.meters_exist_indicator}"></i>' +
        '  </a>' +
        '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        }, {
          name: 'id',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a title="' + $translate.instant('Go to Detail Page') + '" class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
          '    <i class="ui-grid-icon-info-circled"></i>' +
          '  </a>' +
          '  <a title="' + $translate.instant('Go to Detail Page') + '" class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id} : {inventory_type: \'properties\', view_id: row.entity.property_view_id})">' +
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
        }, {
          name: 'labels',
          displayName: '',
          headerCellTemplate: '<i ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents fa fa-chevron-circle-right" id="label-header-icon" style="margin:2px; float:right;"></i>',
          cellTemplate: '<div ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity)"></div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: $scope.get_label_column_width(),
          maxWidth: $scope.max_label_width
        });
      } else {
        $scope.columns.unshift({
          name: 'merged_indicator',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <div title="' + $translate.instant('Merged Records') + '" class="ui-grid-cell-contents merged-indicator">' +
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
          headerCellTemplate: '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a title="' + $translate.instant('Go to Notes') + '" class="ui-grid-cell-contents notes-button" ng-if="row.entity.$$treeLevel === 0" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id, record: row.entity} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id, record: row.entity})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count || \'\' $}</div>' +
          '  </a>' +
          '  <a title="' + $translate.instant('Go to Notes') + '" class="ui-grid-cell-contents notes-button" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id, record: row.entity} : {inventory_type: \'properties\', view_id: row.entity.property_view_id, record: row.entity})">' +
          '    <i class="fa fa-comment" ng-class="{\'text-muted\': !row.entity.notes_count}"></i><div>{$ row.entity.notes_count > 999 ? \'> 999\' : row.entity.notes_count || \'\' $}</div>' +
          '  </a>' +
          '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        }, {
          name: 'id',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a title="' + $translate.instant('Go to Detail Page') + '" class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
          '    <i class="ui-grid-icon-info-circled"></i>' +
          '  </a>' +
          '  <a title="' + $translate.instant('Go to Detail Page') + '" class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id} : {inventory_type: \'properties\', view_id: row.entity.property_view_id})">' +
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
        }, {
          name: 'labels',
          displayName: '',
          headerCellTemplate: '<i ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents fa fa-chevron-circle-right" id="label-header-icon" style="margin:2px; float:right;"></i>',
          cellTemplate: '<div ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity)"></div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: $scope.get_label_column_width(),
          maxWidth: $scope.max_label_width
        });
      }

      var findColumn = _.memoize(function (name) {
        return _.find(all_columns, {name: name});
      });

      // Data
      var processData = function (data) {
        if (_.isUndefined(data)) data = $scope.data;
        var visibleColumns = _.map($scope.columns, 'name')
          .concat(['$$treeLevel', 'notes_count', 'meters_exist', 'merged_indicator', 'id', 'property_state_id', 'property_view_id', 'taxlot_state_id', 'taxlot_view_id']);

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

      // evaluate all derived columns and add the results to the table
      var evaluateDerivedColumns = function () {
        const batch_size = 100;
        const batched_inventory_ids = [];
        let batch_index = 0;
        while (batch_index < $scope.data.length) {
          batched_inventory_ids.push(
            $scope.data.slice(batch_index, batch_index + batch_size).map(d => d.id)
          );
          batch_index += batch_size;
        }

        // Find all columns that linked to a derived column.
        // With the associated derived columns evaluate it and attach it to the original column
        const visible_columns_with_derived_columns = $scope.columns.filter(col => col.derived_column);
        const derived_column_ids = visible_columns_with_derived_columns.map(col => col.derived_column);
        const attached_derived_columns = derived_columns_payload.derived_columns.filter(col => derived_column_ids.includes(col.id))
        column_name_lookup = {}
        visible_columns_with_derived_columns.forEach(col => (column_name_lookup[col.column_name] = col.name))

        const all_evaluation_results = [];
        for (const col of attached_derived_columns) {
          all_evaluation_results.push(...batched_inventory_ids.map(ids => {
            return derived_columns_service.evaluate($scope.organization.id, col.id, $scope.cycle.selected_cycle.id, ids)
              .then(res => {
                formatted_results = res.results.map(x => typeof (x.value) == 'number' ? ({ ...x, 'value': _.round(x.value, $scope.organization.display_decimal_places) }) : x)
                return {derived_column_id: col.id, results: formatted_results};
              });
          }));
        }

        $q.all(all_evaluation_results).then(results => {
          const aggregated_results = {};
          results.forEach(result => {
            if (result.derived_column_id in aggregated_results) {
              aggregated_results[result.derived_column_id].push(...result.results);
            } else {
              aggregated_results[result.derived_column_id] = result.results;
            }
          });

          // finally, update the data to include the calculated values
          $scope.data.forEach(row => {
            Object.entries(aggregated_results).forEach(([derived_column_id, results]) => {
              const derived_column = attached_derived_columns.find(col => col.id == derived_column_id);
              const result = results.find(res => res.id == row.id) || {};
              row[column_name_lookup[derived_column.name]] = result.value;
            });
          });
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
          evaluateDerivedColumns();
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
          filterUsingLabels();
        });
      };

      processData();

      $scope.open_ubid_decode_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/ubid_decode_modal.html',
          controller: 'ubid_decode_modal_controller',
          resolve: {
            property_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_view_id');
            },
            taxlot_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_view_id');
            }
          }
        });
      };

      $scope.open_geocode_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/geocode_modal.html',
          controller: 'geocode_modal_controller',
          resolve: {
            property_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_view_id');
            },
            taxlot_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_view_id');
            },
            org_id: function () {
              return $scope.organization.id;
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
            property_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_view_id');
            },
            taxlot_view_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'taxlots') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'taxlot_view_id');
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
          backdrop: 'static',
          resolve: {
            ids: function () {
              var viewId = $scope.inventory_type === 'properties' ? 'property_view_id' : 'taxlot_view_id';
              var visibleRowIds = _.map($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), function (row) {
                return row.entity[viewId];
              });
              var selectedRowIds = _.map($scope.gridApi.selection.getSelectedRows(), viewId);
              return _.filter(visibleRowIds, function (id) {
                return _.includes(selectedRowIds, id);
              });
            },
            filter_header_string: function () {
              if ($scope.selected_labels.length) {
                return [
                  'Filter Method: ""',
                  $scope.labelLogic,
                  '"", Filter Labels: "',
                  $scope.selected_labels.map(label => label.name).join(' - '),
                  '"'
                ].join('');
              }
              return 'Filter Method: ""none""';
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

      $scope.open_refresh_metadata_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/refresh_metadata_modal.html',
          controller: 'refresh_metadata_modal_controller',
          backdrop: 'static',
          resolve: {
            ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel == 0;
                return !_.has(row, '$$treeLevel');
              }), 'id');
            },
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
            },
            inventory_type: _.constant($scope.inventory_type),
          }
        });
      }

      $scope.open_analyses_modal = function () {
        const modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_detail_analyses_modal.html',
          controller: 'inventory_detail_analyses_modal_controller',
          resolve: {
            inventory_ids: function () {
              return _.map(_.filter($scope.gridApi.selection.getSelectedRows(), function (row) {
                if ($scope.inventory_type === 'properties') return row.$$treeLevel === 0;
                return !_.has(row, '$$treeLevel');
              }), 'property_view_id');
            },
            cycles: _.constant(cycles.cycles),
            current_cycle: _.constant($scope.cycle.selected_cycle)
          }
        });
        modalInstance.result.then(function (data) {
          setTimeout(() => {
            Notification.primary('<a href="#/analyses" style="color: #337ab7;">Click here to view your analyses</a>');
          }, 1000);
        }, function () {
          // Modal dismissed, do nothing
        });
      };

      $scope.view_notes = function (record) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/notes_modal.html',
          controller: 'notes_controller',
          size: 'lg',
          resolve: {
            inventory_type: _.constant(record.inventory_type),
            view_id: _.constant(record.view_id),
            inventory_payload: ['$state', '$stateParams', 'inventory_service', function ($state, $stateParams, inventory_service) {
              return record.inventory_type === 'properties' ? inventory_service.get_property(record.view_id) : inventory_service.get_taxlot(record.view_id);
            }],
            organization_payload: _.constant(organization_payload),
            notes: ['note_service', function (note_service) {
              return note_service.get_notes($scope.organization.id, record.inventory_type, record.view_id);
            }]
          }
        }).result.then(function (notes_count) {
          record.record.notes_count = notes_count;
        });
      };

      function currentColumns () {
        // Save all columns except first 3
        var gridCols = _.filter($scope.gridApi.grid.columns, function (col) {
          return !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'notes_count', 'meters_exist', 'merged_indicator', 'id', 'labels'], col.name)
            && col.visible
            && !col.colDef.is_derived_column;
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
            inventory_service.update_column_list_profile(id, profile);
          });
        } else {
          var id = $scope.currentProfile.id;
          var profile = _.omit($scope.currentProfile, 'id');
          profile.columns = currentColumns();
          inventory_service.update_column_list_profile(id, profile);
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
        exporterMenuCsv: false,
        exporterMenuExcel: false,
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
            staticColIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'meters_exist'});
            if (staticColIndex !== 4) {
              col = $scope.gridApi.grid.columns[staticColIndex];
              $scope.gridApi.grid.columns.splice(staticColIndex, 1);
              $scope.gridApi.grid.columns.splice(4, 0, col);
            }
            staticColIndex = _.findIndex($scope.gridApi.grid.columns, {name: 'id'});
            if (staticColIndex !== 5) {
              col = $scope.gridApi.grid.columns[staticColIndex];
              $scope.gridApi.grid.columns.splice(staticColIndex, 1);
              $scope.gridApi.grid.columns.splice(5, 0, col);
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

            if ($scope.gridApi) {
              uiGridGridMenuService.removeFromGridMenu($scope.gridApi.grid, 'dynamic-export');
              $scope.gridApi.core.addToGridMenu($scope.gridApi.grid, [{
                id: 'dynamic-export',
                title: ($scope.selectedCount == 0 ? 'Export All' : 'Export Selected'),
                order: 100,
                action: function ($event) {
                  $scope.open_export_modal();
                }
              }]);
            }

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
            selectionChanged();
          });

          // Load the initial data
          refresh_objects();
        }
      };

    }]);
