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
    'goal_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      goal,
      cycles,
      goal_service
    ) {
      $scope.current_cycle = undefined;
      $scope.cycles = cycles;

      $scope.save = () => {
        console.log($scope.current_cycle)
        goal_service.create_cycle_goal(goal.id, $scope.current_cycle).then(() => {
          console.log("asdf")
          $state.reload();
          $uibModalInstance.dismiss();
        });
      };

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
