/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_data_logger_upload_modal', []).controller('delete_data_logger_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'uiGridConstants',
  '$window',
  'spinner_utility',
  'sensor_service',
  'organization_id',
  'data_logger_id',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    uiGridConstants,
    $window,
    spinner_utility,
    sensor_service,
    organization_id,
    data_logger_id
  ) {
    $scope.delete = () => {
      sensor_service.delete_data_logger(data_logger_id, organization_id)
      .then( () => {
        spinner_utility.show();
        $window.location.reload();
      })
      .catch((err) => Notification.error(err));
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
