/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('SEED.controller.copy_to_different_cycle_modal', []).controller('copy_to_different_cycle_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'inventory_service',
  'org',
  'cycles',
  'view_ids',
  'profiles',
  'spinner_utility',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    inventory_service,
    org,
    cycles,
    view_ids,
    profiles,
    spinner_utility,
  ) {
    $scope.selected_cycle = null;
    $scope.selected_column_list_profile = null;
    $scope.cycles = cycles;
    $scope.profiles = profiles;

    $scope.save = () => {
      spinner_utility.show();
      inventory_service.copy_to_cycle(
        cycle_id=$scope.selected_cycle.id,
        view_ids=view_ids,
        column_ids=$scope.selected_column_list_profile.columns.map(c => c.id)
      ).then(data => {
        console.log(data)
      }).finally(() => {
          spinner_utility.hide();
          $uibModalInstance.close();
      });
    }

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
