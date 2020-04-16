/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.confirm_column_settings_modal', [])
  .controller('confirm_column_settings_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'all_columns',
    'cycle_service',
    'inventory_service',
    'inventory_type',
    'org_id',
    'organization_service',
    'proposed_changes',
    'spinner_utility',
    'uiGridGroupingConstants',
    function (
      $scope,
      $uibModalInstance,
      all_columns,
      cycle_service,
      inventory_service,
      inventory_type,
      org_id,
      organization_service,
      proposed_changes,
      spinner_utility,
      uiGridGroupingConstants
    ) {
      $scope.inventory_type = inventory_type;
      $scope.org_id = org_id;
      $scope.all_columns = all_columns;

      $scope.step = {
        number: 1,
      }

      $scope.goto_step = function (step) {
        $scope.step.number = step;
      };

      cycle_service.get_cycles_for_org($scope.org_id).then(function (cycles) {
        $scope.cycles = cycles.cycles;
      });

      // parse proposed changes to create change summary to be presented to user
      var all_changed_settings = ["column_name"];  // add column_name to describe each row
      $scope.change_summary_data = _.reduce(proposed_changes, function (summary, value, key) {
        var column = _.find($scope.all_columns, {id: parseInt(key)});
        var change = _.pick(_.cloneDeep(column), ['column_name']);

        // capture changed setting values
        summary.push(_.merge(change, value));

        // capture corresponding settings columns
        all_changed_settings = _.concat(all_changed_settings, _.keys(value));
        return summary;
      }, []);

      var base_summary_column_defs = [
        {
          field: 'column_name'
        },
        {
          field: 'display_name',
          displayName: 'Display Name Change',
        },
        {
          field: 'geocoding_order',
          displayName: 'Geocoding Order',
          cellTemplate: '<div class="ui-grid-cell-contents text-center">' +
              '<span style="display: flex; align-items:center;">' +
                '<span style="margin-right: 5px;">' +
                  '<input type="checkbox" ng-checked="row.entity.geocoding_order" class="no-click">' +
                '</span>' +
                '<select class="form-control input-sm" ng-disabled=true><option value="">{$:: row.entity.geocoding_order || \'\' $}</option></select>' +
              '</span>' +
            '</div>',
        },
        {
          field: 'data_type',
          displayName: 'Data Type Change',
        },
        {
          field: 'merge_protection',
          displayName: 'Merge Protection Change',
          cellTemplate: '<div class="ui-grid-cell-contents text-center">' +
            '<input type="checkbox" class="no-click" ng-show="{$ row.entity.merge_protection != undefined $}" ng-checked="{$ row.entity.merge_protection === \'Favor Existing\' $}" style="margin: 0px;">' +
            '</div>',
        },
        {
          field: 'recognize_empty',
          displayName: 'Recognize Empty',
          cellTemplate: '<div class="ui-grid-cell-contents text-center">' +
            '<input type="checkbox" class="no-click" ng-hide="{$ row.entity.recognize_empty === undefined $}" ng-checked="{$ row.entity.recognize_empty === true $}" style="margin: 0px;">' +
            '</div>',
        },
        {
          field: 'is_matching_criteria',
          displayName: 'Matching Criteria Change',
          cellTemplate: '<div class="ui-grid-cell-contents text-center">' +
            '<input type="checkbox" class="no-click" ng-hide="{$ row.entity.is_matching_criteria === undefined $}" ng-checked="{$ row.entity.is_matching_criteria === true $}" style="margin: 0px;">' +
            '</div>',
        },
      ]

      var unique_summary_columns = _.uniq(all_changed_settings);
      $scope.change_summary_column_defs = _.filter(base_summary_column_defs, function (column_def) {
        return _.includes(unique_summary_columns, column_def.field);
      });

      $scope.change_summary = {
        data: $scope.change_summary_data,
        columnDefs: $scope.change_summary_column_defs,
        enableColumnResizing: true,
        rowHeight: 40,
        minRowsToShow: Math.min($scope.change_summary_data.length, 5),
      };

      // By default, assume matching criteria isn't being updated to exclude PM Property ID
      // And since warning wouldn't be shown in that case, set "acknowledged" to true.
      $scope.checks = {
        matching_criteria_excludes_pm_property_id: false,
        warnings_acknowledged: true,
      }

      // Check if PM Property ID is actually being removed from matching criteria
      if (_.find($scope.change_summary_data, {column_name: "pm_property_id", is_matching_criteria: false})) {
        $scope.checks.matching_criteria_excludes_pm_property_id = true;
        $scope.checks.warnings_acknowledged = false;
      }

      // Preview
      // Agg function returning last value of matching criteria field (all should be the same if they match)
      $scope.matching_field_value = function(aggregation, fieldValue) {
        aggregation.value = fieldValue;
      };

      var prioritize_sort = function (grid, sortColumns) {
        // To maintain grouping while giving users the ability to have some sorting,
        // matching columns are given top priority followed by the hidden linking ID column.
        // Lastly, non-matching columns are given next priority so that users can sort within a grouped set.
        if (sortColumns.length > 1) {
          var matching_cols = _.filter(sortColumns, function (col) {
              return col.colDef.is_matching_criteria;
          });
          var linking_id_col = _.find(sortColumns, ['name', 'id']);
          var remaining_cols = _.filter(sortColumns, function (col) {
            return !col.colDef.is_matching_criteria && !(col.name === 'id');
          });
          sortColumns = matching_cols.concat(linking_id_col).concat(remaining_cols);
          _.forEach(sortColumns, function (col, index) {
            col.sort.priority = index;
          })
        }
      };

      // Takes raw cycle-partitioned records and returns array of cycle-aware records
      var format_preview_records = function(raw_inventory) {
        return _.reduce(raw_inventory, function(all_records, records, cycle_id) {
          var cycle = _.find($scope.cycles, { id: parseInt(cycle_id) });
          _.forEach(records, function(record) {
            record.cycle_name = cycle.name;
            record.cycle_start = cycle.start;
            all_records.push(record)
          })
          return all_records
        }, []);
      };

      // Builds preview columns using non-extra_data columns
      var build_preview_columns = function () {
        // create copy in order to not change original column objects.
        var preview_column_defs = _.reject(_.cloneDeep($scope.all_columns), 'is_extra_data');
        var default_min_width = 50;
        var autopin_width = 100;
        var column_def_defaults = {
          headerCellFilter: 'translate',
          minWidth: default_min_width,
          width: 125,
          groupingShowAggregationMenu: false,
        };

        _.map(preview_column_defs, function (col) {
          var options = {};
          if (col.data_type === 'datetime') {
            options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
            options.filter = inventory_service.dateFilter();
          } else {
            options.filter = inventory_service.combinedFilter();
          }

          // For matching criteria values, always pin left and show values in aggregate rows.
          if ($scope.proposed_matching_criteria_columns.includes(col.column_name)) {
            col.pinnedLeft = true;

            // Help indicate matching columns are given preferred sort priority
            col.displayName = col.displayName + '*';
            options.headerCellClass = "matching-column-header";

            options.customTreeAggregationFn = $scope.matching_field_value;
            options.width = autopin_width;
          }
          return _.defaults(col, options, column_def_defaults);
        });

        // Grouping Settings
        preview_column_defs.unshift(
          {
            displayName: 'Linking ID',
            grouping: { groupPriority: 0 },
            name: 'id',
            sort: { priority: 0, direction: 'desc' },
            pinnedLeft: true,
            visible: false,
            suppressRemoveSort: true, // since grouping relies on sorting
            minWidth: default_min_width,
            width: autopin_width,
          },
          {
            name: "cycle_name",
            displayName: "Cycle",
            pinnedLeft: true,
            treeAggregationType: uiGridGroupingConstants.aggregation.COUNT,
            customTreeAggregationFinalizerFn: function (aggregation) {
              aggregation.rendered = "total cycles: " + aggregation.value;
            },
            minWidth: default_min_width,
            width: autopin_width,
            groupingShowAggregationMenu: false,
          },
          {
            name: "cycle_start",
            displayName: "Cycle Start",
            cellFilter: 'date:\'yyyy-MM-dd\'',
            filter: inventory_service.dateFilter(),
            type: 'date',
            sort: { priority: 1, direction: 'asc' },
            pinnedLeft: true,
            minWidth: default_min_width,
            width: autopin_width,
            groupingShowAggregationMenu: false,
          },
        )

      return preview_column_defs;
      };

      // Initialize preview table as empty for now.
      $scope.match_merge_link_preview = {
        data: 'data',
        enableColumnResizing: true,
        enableFiltering: true,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          // used to allow filtering for child branches of grouping tree
          $scope.gridApi.table_category = 'year-over-year';

          $scope.gridApi.core.on.filterChanged($scope, function () {
          // This is a workaround for losing the state of expanded rows during filtering.
              _.delay($scope.gridApi.treeBase.expandAllRows, 500);
          })

          // Prioritized to maintain grouping.
          $scope.gridApi.core.on.sortChanged($scope, prioritize_sort);
        },
      };

      // Preview Loading Helpers
      var build_proposed_matching_columns = function (result) {
        // Summarize proposed matching_criteria_columns for pinning and to create preview
        var criteria_additions = _.filter($scope.change_summary_data, function (change) {
            return change.is_matching_criteria
        });
        var criteria_removals = _.filter($scope.change_summary_data, function (change) {
            return change.is_matching_criteria === false;
        });

        $scope.criteria_changes = {
          add: _.map(criteria_additions, 'column_name'),
          remove: _.map(criteria_removals, 'column_name'),
        }

        var base_and_add;
        if ($scope.inventory_type == "properties") {
          base_and_add = _.union(result.PropertyState, $scope.criteria_changes.add);
        } else {
          base_and_add = _.union(result.TaxLotState, $scope.criteria_changes.add);
        }
        $scope.proposed_matching_criteria_columns = _.difference(base_and_add, $scope.criteria_changes.remove);
      };

      var build_preview = function (summary) {
        $scope.data = format_preview_records(summary);
        $scope.preview_columns = build_preview_columns();
        $scope.match_merge_link_preview.columnDefs = $scope.preview_columns;
      };

      var preview_loading_complete = function () {
        $scope.preview_loading = false;
        spinner_utility.hide();
      };

      var get_preview = function () {
        // Use new proposed matching_criteria_columns to request a preview then render this preview.
        var spinner_options = {
          scale: 0.40,
          position: "relative",
          left: "100%",
        }
        spinner_utility.show(spinner_options, $('#spinner_placeholder')[0]);

        organization_service.match_merge_link_preview($scope.org_id, $scope.inventory_type, $scope.criteria_changes)
          .then(function (response) {
            organization_service.check_match_merge_link_status(response.progress_key)
            .then(function (completion_notice) {
              organization_service.get_match_merge_link_result($scope.org_id, completion_notice.unique_id)
                .then(build_preview)
                .then(preview_loading_complete);
            });
          });
      };

      // Get and Show Preview (If matching criteria changes exist.)
      $scope.matching_criteria_exists = _.find(_.values($scope.change_summary_data), function(delta) {
        return _.has(delta, 'is_matching_criteria');
      });

      if ($scope.matching_criteria_exists) {
        $scope.preview_loading = true;

        organization_service.matching_criteria_columns($scope.org_id)
          .then(build_proposed_matching_columns)
          .then(get_preview);
      }

      $scope.confirm = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
