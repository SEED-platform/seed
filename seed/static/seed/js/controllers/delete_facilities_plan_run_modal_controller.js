/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.delete_facilities_plan_run_modal', [])
  .controller('delete_facilities_plan_run_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'facilities_plan_run',
    'facilities_plan_run_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      facilities_plan_run,
      facilities_plan_run_service,
    ) {
      $scope.facilities_plan_run = facilities_plan_run;

      $scope.delete = () => {
        facilities_plan_run_service.delete_facilities_plan_run(facilities_plan_run.id).then(() => {
          $state.reload();
          $uibModalInstance.dismiss();
        });
      }

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
