/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.create_cycle_goal_modal', [])
  .controller('create_cycle_goal_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'goal',
    'cycles',
    'annual_reports',
    'goal_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      goal,
      cycles,
      annual_reports,
      goal_service
    ) {
      $scope.current_cycle = undefined;
      $scope.annual_report = undefined;
      $scope.cycles = cycles;
      $scope.annual_reports = annual_reports.results;

      $scope.save = () => {
        console.log($scope.annual_report?.id, $scope.annual_report?.name)
        goal_service.create_cycle_goal(goal.id, $scope.current_cycle, $scope.annual_report?.id, $scope.annual_report?.name).then(() => {
          $state.reload();
          $uibModalInstance.dismiss();
        });
      };

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
