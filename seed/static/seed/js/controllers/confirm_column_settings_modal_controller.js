/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.confirm_column_settings_modal', []).controller('confirm_column_settings_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'all_columns',
  'columns',
  'cycle_service',
  'inventory_service',
  'inventory_type',
  'org_id',
  'organization_service',
  'proposed_changes',
  'spinner_utility',
  'uiGridGroupingConstants',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    all_columns,
    columns,
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
    $scope.columns = columns;

    $scope.step = {
      number: 1
    };

    $scope.goto_step = function (step) {
      $scope.step.number = step;
    };

    cycle_service.get_cycles_for_org($scope.org_id).then((cycles) => {
      $scope.cycles = cycles.cycles;
    });

    // parse proposed changes to create change summary to be presented to user
    let all_changed_settings = ['column_name']; // add column_name to describe each row
    $scope.change_summary_data = _.reduce(
      proposed_changes,
      (summary, value, key) => {
        const column = _.find($scope.columns, { id: parseInt(key) });
        const change = _.pick(_.cloneDeep(column), ['column_name']);

        // capture changed setting values
        summary.push(_.merge(change, value));

        // capture corresponding settings columns
        all_changed_settings = _.concat(all_changed_settings, _.keys(value));
        return summary;
      },
      []
    );

    // If a preexisting ComStock mapping exists on the other table add it to the diff list for removal
    _.forEach($scope.change_summary_data, (diff) => {
      if (!_.isNil(diff.comstock_mapping)) {
        const found = _.find(all_columns, { related: true, comstock_mapping: diff.comstock_mapping });
        if (found) {
          $scope.change_summary_data.push({
            column_name: `${found.column_name} (${found.table_name})`,
            comstock_mapping: null
          });
        }
      }
    });

    const base_summary_column_defs = [
      {
        field: 'column_name'
      },
      {
        field: 'displayName',
        displayName: 'Display Name Change'
      },
      {
        field: 'geocoding_order',
        displayName: 'Geocoding Order',
        cellTemplate:
          '<div class="ui-grid-cell-contents text-center">' +
          '<span style="display: flex; align-items:center;">' +
          '<span style="margin-right: 5px;">' +
          '<input type="checkbox" ng-checked="row.entity.geocoding_order" class="no-click">' +
          '</span>' +
          '<select class="form-control input-sm" ng-disabled=true><option value="">{$:: row.entity.geocoding_order || \'\' $}</option></select>' +
          '</span>' +
          '</div>'
      },
      {
        field: 'data_type',
        displayName: 'Data Type Change'
      },
      {
        field: 'merge_protection',
        displayName: 'Merge Protection Change',
        cellTemplate:
          '<div class="ui-grid-cell-contents text-center">' +
          '<input type="checkbox" class="no-click" ng-show="{$ row.entity.merge_protection != undefined $}" ng-checked="{$ row.entity.merge_protection === \'Favor Existing\' $}" style="margin: 0;">' +
          '</div>'
      },
      {
        field: 'recognize_empty',
        displayName: 'Recognize Empty',
        cellTemplate:
          '<div class="ui-grid-cell-contents text-center">' +
          '<input type="checkbox" class="no-click" ng-hide="{$ row.entity.recognize_empty === undefined $}" ng-checked="{$ row.entity.recognize_empty === true $}" style="margin: 0;">' +
          '</div>'
      },
      {
        field: 'is_matching_criteria',
        displayName: 'Matching Criteria Change',
        cellTemplate:
          '<div class="ui-grid-cell-contents text-center">' +
          '<input type="checkbox" class="no-click" ng-hide="{$ row.entity.is_matching_criteria === undefined $}" ng-checked="{$ row.entity.is_matching_criteria === true $}" style="margin: 0;">' +
          '</div>'
      },
      {
        field: 'comstock_mapping',
        displayName: 'ComStock Mapping Change',
        cellTemplate:
          '<div class="ui-grid-cell-contents">{$ row.entity.comstock_mapping === undefined ? "" : row.entity.comstock_mapping === null ? "(removed)" : "comstock." + row.entity.comstock_mapping | translate $}</div>'
      }
    ];

    const unique_summary_columns = _.uniq(all_changed_settings);
    $scope.change_summary_column_defs = _.filter(base_summary_column_defs, (column_def) => _.includes(unique_summary_columns, column_def.field));

    $scope.change_summary = {
      data: $scope.change_summary_data,
      columnDefs: $scope.change_summary_column_defs,
      enableColumnResizing: true,
      rowHeight: 40,
      minRowsToShow: Math.min($scope.change_summary_data.length, 5)
    };

    // By default, assume matching criteria isn't being updated to exclude PM Property ID
    // And since warning wouldn't be shown in that case, set "acknowledged" to true.
    $scope.checks = {
      matching_criteria_excludes_pm_property_id: false,
      warnings_acknowledged: true
    };

    // Check if PM Property ID is actually being removed from matching criteria
    if (_.find($scope.change_summary_data, { column_name: 'pm_property_id', is_matching_criteria: false })) {
      $scope.checks.matching_criteria_excludes_pm_property_id = true;
      $scope.checks.warnings_acknowledged = false;
    }

    if ($scope.matching_criteria_exists) {
      organization_service.matching_criteria_columns($scope.org_id);
    }

    $scope.confirm = function () {
      $uibModalInstance.close();
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss();
    };
  }
]);
