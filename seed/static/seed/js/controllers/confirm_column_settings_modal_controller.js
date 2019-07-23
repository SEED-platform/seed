/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.confirm_column_settings_modal', [])
  .controller('confirm_column_settings_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'all_columns',
    'proposed_changes',
    function (
      $scope,
      $uibModalInstance,
      all_columns,
      proposed_changes
    ) {
      // parse proposed changes to create change summary to be presented to user
      var all_changed_settings = ["column_name"];  // add column_name to describe each row
      $scope.change_summary_data = _.reduce(proposed_changes, function (summary, value, key) {
        var column = _.find(all_columns, {id: parseInt(key)});
        var change = _.pick(column, ['column_name']);

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
        minRowsToShow: Math.min($scope.change_summary_data.length, 5),
      };

      $scope.confirm = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
