/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('SEED.controller.copy_to_different_cycle_modal', []).controller('copy_to_different_cycle_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'inventory_service',
  'uploader_service',
  'cycles',
  'view_ids',
  'profiles',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    inventory_service,
    uploader_service,
    cycles,
    view_ids,
    profiles
  ) {
    $scope.selected_cycle = null;
    $scope.selected_column_list_profile = null;
    $scope.cycles = cycles;
    $scope.profiles = profiles;
    $scope.status = {
      progress: 0,
      status_message: '',
      in_progress: true,
      complete: false,
      result: {}
    };

    $scope.save = () => {
      $scope.status.in_progress = true;
      inventory_service.copy_to_cycle(
        cycle_id = $scope.selected_cycle.id,
        view_ids = view_ids,
        column_ids = $scope.selected_column_list_profile.columns.map((c) => c.id)
      ).then((response) => {
        const data = response.data;
        if (response.status !== 200) {
          handle_response(data.message, true);
          $uibModalInstance.close();
        } else {
          uploader_service.check_progress_loop(
            data.progress_key,
            0,
            1,
            (data) => handle_response(data.message),
            (data) => handle_response(data.data.message, true),
            $scope.status
          );
        }
      })
        .catch(() => handle_response('Unexpected Error.', true));
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
