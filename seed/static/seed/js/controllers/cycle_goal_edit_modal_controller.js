/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.cycle_goal_edit_modal', []).controller('cycle_goal_edit_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'goal_service',
  'spinner_utility',
  'goal',
  'cycle_goal',
  'bb_salesforce_enabled',
  'is_logged_into_salesforce',
  'annual_reports',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    goal_service,
    spinner_utility,
    goal,
    cycle_goal,
    bb_salesforce_enabled,
    is_logged_into_salesforce,
    annual_reports,
  ) {
    $scope.goal = goal;
    $scope.cycle_goal = cycle_goal;
    $scope.bb_salesforce_enabled = bb_salesforce_enabled;
    $scope.is_logged_into_salesforce = is_logged_into_salesforce;
    $scope.annual_reports = [...annual_reports.results, {id: null, name: null}];
    $scope.current_cycle = cycle_goal.current_cycle.id;
    $scope.annual_report = $scope.annual_reports.find(ar => ar.id == cycle_goal.salesforce_annual_report_id);

    $scope.change_annual_report = (annual_report) => {
      $scope.annual_report = annual_report;
    }

    $scope.save = () => {
      goal_service.edit_cycle_goal(goal.id, cycle_goal.id, $scope.current_cycle, $scope.annual_report?.id, $scope.annual_report?.name).then(() => {
        $state.reload();
        $uibModalInstance.dismiss();
      });
    };

    $scope.close = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
