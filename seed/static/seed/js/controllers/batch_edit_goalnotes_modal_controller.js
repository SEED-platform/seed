/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.batch_edit_goalnotes_modal', [])
  .controller('batch_edit_goalnotes_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'goal_service',
    'property_view_ids',
    'organization',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      goal_service,
      property_view_ids,
      goal,
      organization,
    ) {
      console.log('modal')

      $scope.settings = {
        question: {selected: false, value: ''},
        resolution: {selected: false, value: ''},
        historical_note: {selected: false, value: ''},
        passed_checks: {selected: false, value: false},
        new_or_acquired: {selected: false, value: false}
      }

      $scope.save = () => {
        console.log('save')
      }
      $scope.close = () => {
        $uibModalInstance.dismiss();
      }
    }
  ]);