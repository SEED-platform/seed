/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.match_merge_modal', []).controller('match_merge_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'spinner_utility',
  'dataset_service',
  'uploader_service',
  'org',
  'property_ubid_matching',
  'taxlot_ubid_matching',
  'Notification',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    spinner_utility,
    dataset_service,
    uploader_service,
    org,
    property_ubid_matching,
    taxlot_ubid_matching,
    Notification
  ) {
    $scope.org = org;
    $scope.cycles = org.cycles;
    $scope.selected_cycle = {};
    $scope.selected_cycle = $scope.cycles[0] || {};
    $scope.property_ubid_matching = property_ubid_matching;
    $scope.taxlot_ubid_matching = taxlot_ubid_matching;

    $scope.uploader = {
      in_progress: false,
      progress: 0,
      complete: false,
      status_message: ''
    };

    spinner_utility.hide();
    $scope.trigger_match_merge = () => {
      dataset_service.match_merge_inventory($scope.selected_cycle.cycle_id).then((data) => {
        $scope.uploader.in_progress = true;
        uploader_service.check_progress_loop(
          data.progress_key,
          0,
          1,
          () => {
            Notification.success('Matched and merged cycle inventory');
            $scope.close();
          },
          () => {
            Notification.error('Unexpected Error');
          },
          $scope.uploader
        );
      });
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
