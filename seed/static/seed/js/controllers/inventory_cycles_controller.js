/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_cycles', [])
  .controller('inventory_cycles_controller', [
    '$scope',
    '$window',
    '$stateParams',
    'inventory_service',
    'inventory',
    'cycles',
    'profiles',
    'current_profile',
    'all_columns',
    'urls',
    'spinner_utility',
    'matching_criteria_columns',
    '$translate',
    'uiGridConstants',
    'uiGridGroupingConstants',
    'i18nService', // from ui-grid
    function (
      $scope,
      $window,
      $stateParams,
      inventory_service,
      inventory,
      cycles,
      profiles,
      current_profile,
      all_columns,
      urls,
      spinner_utility,
      matching_criteria_columns,
      $translate,
      uiGridConstants,
      uiGridGroupingConstants,
      i18nService
    ) {
      spinner_utility.show();
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      // Scope columns/data to only those of the given inventory_type
      var state_type = $scope.inventory_type == "properties" ? "PropertyState" : "TaxLotState";
      $scope.all_columns = _.filter(all_columns, {table_name: state_type});

      // set up i18n
      //
      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // Establish all cycle options and initially included cycles
      $scope.included_cycle_ids = _.map(_.keys(inventory), function (cycle_id) {
        return parseInt(cycle_id);
      });
      $scope.cycle_options = _.map(cycles.cycles, function(cycle) {
        var selected = $scope.included_cycle_ids.includes(cycle.id);
        return {
          selected: selected,
          label: cycle.name,
          value: cycle.id,
          start: cycle.start,
        };
      });

      // Checks for cycle selection changes and refreshes inventory if necessary
      $scope.cycle_selection_toggled = function (is_open) {
        if (!is_open) {
          var updated_selections = _.map(_.filter($scope.cycle_options, ['selected', true]), 'value');
          if (!_.isEqual($scope.included_cycle_ids, updated_selections)) {
            $scope.included_cycle_ids = updated_selections;
            inventory_service.save_last_selected_cycles(updated_selections);
            $scope.refresh_objects();
          }
        }
      };

      // Takes raw cycle-partitioned records and returns array of cycle-aware records
      $scope.format_records = function(raw_inventory) {
        return _.reduce(raw_inventory, function(all_records, records, cycle_id) {
          var cycle = _.find($scope.cycle_options, { value: parseInt(cycle_id) });
          _.forEach(records, function(record) {
            record.cycle_name = cycle.label;
            record.cycle_start = cycle.start;
            all_records.push(record)
          })
          return all_records
        }, []);
      };

      // Set initial table data
      $scope.data = $scope.format_records(inventory);

      // Refreshes inventory by making API call
      $scope.refresh_objects = function() {
        spinner_utility.show();
        var profile_id = _.has($scope.currentProfile, 'id') ? $scope.currentProfile.id : undefined;
        if ($scope.inventory_type == "properties") {
          inventory_service.properties_cycle(profile_id, $scope.included_cycle_ids).then(function(refreshed_inventory) {
            $scope.data = $scope.format_records(refreshed_inventory);
            spinner_utility.hide();
          });
        } else {
          inventory_service.taxlots_cycle(profile_id, $scope.included_cycle_ids).then(function(refreshed_inventory) {
            $scope.data = $scope.format_records(refreshed_inventory);
            spinner_utility.hide();
          });
        }
      };

      // On profile change, refreshes objects and rebuild columns
      $scope.profile_change = function() {
        inventory_service.save_last_profile($scope.currentProfile.id, $scope.inventory_type);
        $scope.refresh_objects();

        // uiGrid doesn't recognize complete columnDefs swap unless it's removed and refreshed and notified for each
        $scope.gridOptions.columnDefs = [];
        $scope.gridApi.core.notifyDataChange(uiGridConstants.dataChange.COLUMN)

        $scope.build_columns();

        $scope.gridOptions.columnDefs = $scope.columns;
        $scope.gridApi.core.notifyDataChange(uiGridConstants.dataChange.COLUMN)
      };

      // Agg function returning last value of matching criteria field (all should be the same if they match)
      $scope.matching_field_value = function(aggregation, fieldValue) {
        aggregation.value = fieldValue;
      };

      // matching_criteria_columns identified here to pin left on table
      if ($scope.inventory_type == "properties") {
        $scope.matching_criteria_columns = matching_criteria_columns.PropertyState;
      } else {
        $scope.matching_criteria_columns = matching_criteria_columns.TaxLotState;
      }

      // Builds columns with profile, default, and grouping settings
      $scope.build_columns = function() {
        $scope.columns = [];

        // Profile Settings
        if ($scope.currentProfile) {
          _.forEach($scope.currentProfile.columns, function (col) {
            var foundCol = _.find($scope.all_columns, {id: col.id});
            if (foundCol) {
              foundCol.pinnedLeft = col.pinned;
              $scope.columns.push(foundCol);
            }
          });
        } else {
          // No profiles exist
          $scope.columns = _.reject($scope.all_columns, 'is_extra_data');
        }

        // Default Settings
        var column_def_defaults = {
          headerCellFilter: 'translate',
          minWidth: 75,
          width: 150
        };

        _.map($scope.columns, function (col) {
          var options = {};
          if (col.data_type === 'datetime') {
            options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
            options.filter = inventory_service.dateFilter();
          } else {
            options.filter = inventory_service.combinedFilter();
          }
          // else if (['eui', 'interger'].includes(col.data_type)) {
          //   options.cellTemplate = '<div ng-if="row.groupHeader" class="ui-grid-cell-contents" tooltip-append-to-body="true" tooltip-popup-delay="500" title="TOOLTIP">[tooltip-placeholder?]</div>' +
          //     '<div ng-if="!row.groupHeader" class="ui-grid-cell-contents">{{COL_FIELD CUSTOM_FILTERS}}</div>'
          // }

          // For matching criteria values, always pin left and show values in aggregate rows.
          if ($scope.matching_criteria_columns.includes(col.column_name)) {
            col.pinnedLeft = true;
            options.customTreeAggregationFn = $scope.matching_field_value;
          }
          return _.defaults(col, options, column_def_defaults);
        });

        // Grouping Settings
        $scope.columns.unshift(
          {
            displayName: 'Linking ID',
            grouping: { groupPriority: 0 },
            name: 'id',
            sort: { priority: 0, direction: 'desc' },
            pinnedLeft: true,
            visible: false,
            minWidth: 75,
            width: 150
          },
          {
            name: 'inventory detail link icon',
            displayName: '',
            cellTemplate: '<div class="ui-grid-row-header-link">' +
            '  <a class="ui-grid-cell-contents" ng-if="!row.groupHeader" ui-sref="inventory_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', view_id: row.entity.property_view_id} : {inventory_type: \'taxlots\', view_id: row.entity.taxlot_view_id})">' +
            '    <i class="ui-grid-icon-info-circled"></i>' +
            '  </a>' +
            '</div>',
            enableColumnMenu: false,
            enableColumnMoving: false,
            enableColumnResizing: false,
            enableFiltering: false,
            enableHiding: false,
            enableSorting: false,
            pinnedLeft: true,
            visible: true,
            width: 30
          },
          {
            name: "cycle_name",
            displayName: "Cycle",
            pinnedLeft: true,
            treeAggregationType: uiGridGroupingConstants.aggregation.COUNT,
            minWidth: 75,
            width: 150
          },
          {
            name: "cycle_start",
            displayName: "Cycle Start",
            cellFilter: 'date:\'yyyy-MM-dd\'',
            type: 'date',
            sort: { priority: 1, direction: 'asc' },
            pinnedLeft: true,
            minWidth: 75,
            width: 110
          },
        )
      };

      $scope.build_columns();

      // $scope.expandedRows = [];

      $scope.gridOptions = {
        columnDefs: $scope.columns,
        data: 'data',
        enableColumnResizing: true,
        enableFiltering: true,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          // used to allow filtering for child branches of grouping tree
          $scope.gridApi.table_category = 'year-over-year';

          // $scope.gridApi.treeBase.on.rowExpanded($scope, function(row) {
          //   $scope.expandedRows.unshift(row);
          // })
          //
          // $scope.gridApi.treeBase.on.rowCollapsed($scope, function(row) {
          //   _.remove($scope.expandedRows, function(expanded) {
          //     return expanded == row;
          //   });
          // })
          //
          // // $scope.gridApi.core.on.rowsRendered($scope, function() {
          // // $scope.gridApi.core.on.renderingComplete($scope, function() {
          // $scope.gridApi.core.on.filterChanged($scope, function() {
          //   console.log('expanded', $scope.expandedRows);
          //   console.log('visible', $scope.gridApi.core.getVisibleRows());
          //   debugger;
          //   _.forEach(_.intersection($scope.gridApi.core.getVisibleRows(), $scope.expandedRows), function(row) {
          //     $scope.gridApi.treeBase.expandRow(row, true);
          //   });
          //   // $scope.gridApi.treeBase.getTreeExpandedState() not available?
          //   // $scope.gridApi.treeBase.setTreeState() not available?
          // })

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        },
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };

      spinner_utility.hide();
    }]);
