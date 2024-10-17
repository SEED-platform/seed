/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.update_derived_data_modal', []).controller('update_derived_data_modal_controller', [
  '$scope',
  '$state',
  '$q',
  '$uibModalInstance',
  'inventory_service',
  'Notification',
  'uploader_service',
  'property_view_ids',
  'taxlot_view_ids',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $q,
    $uibModalInstance,
    inventory_service,
    Notification,
    uploader_service,
    property_view_ids,
    taxlot_view_ids
  ) {
    $scope.property_view_ids = _.uniq(property_view_ids);
    $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);

    $scope.status = 'ready';
    $scope.uploader = { progress: 0 };

    $scope.begin_update = () => {
      inventory_service.update_derived_data($scope.property_view_ids, $scope.taxlot_view_ids).then((data) => {
        Notification.primary('Updating derived columns. This may take a few minutes...');
        $scope.status = 'in progress';

        const resultHandler = (notification_type, message) => {
          $uibModalInstance.close();
          Notification[notification_type](message);
          $state.reload();
        };

        uploader_service.check_progress_loop(
          data.progress_key,
          0,
          1,
          () => resultHandler('success', 'Derived columns updated'),
          () => resultHandler('error', 'Unexpected Error'),
          $scope.uploader
        );
      });
    };

    /**
     * cancel: dismisses the modal
     */
    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
