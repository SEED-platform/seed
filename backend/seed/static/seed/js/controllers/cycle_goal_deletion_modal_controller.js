/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.cycle_goal_deletion_modal', []).controller('cycle_goal_deletion_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'goal_service',
  'spinner_utility',
  'organization_id',
  'goal',
  'cycle_goal',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    goal_service,
    spinner_utility,
    organization_id,
    goal,
    cycle_goal
  ) {
    $scope.cycle_goal_name = `${goal.name} - ${cycle_goal.current_cycle.name}`;

    $scope.delete_cycle_goal = () => {
      spinner_utility.show();
      goal_service.delete_cycle_goal(goal.id, cycle_goal.id).then(() => {
        spinner_utility.show();
        $uibModalInstance.dismiss('cancel');
      });
      $state.reload();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };
  }
]);
