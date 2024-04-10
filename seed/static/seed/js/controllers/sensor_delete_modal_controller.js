/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.sensor_delete_modal', []).controller('sensor_delete_modal_controller', [
  '$scope',
  '$state',
  '$stateParams',
  '$uibModalInstance',
  '$window',
  'uiGridConstants',
  'spinner_utility',
  'organization_id',
  'sensor',
  'sensor_service',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $stateParams,
    $uibModalInstance,
    $window,
    uiGridConstants,
    spinner_utility,
    organization_id,
    sensor,
    sensor_service
  ) {
    $scope.delete = () => {
      spinner_utility.show();
      sensor_service.delete_sensor($stateParams.view_id, sensor.id, organization_id)
        .then(() => {
          $window.location.reload();
        })
        .catch((err) => Notification.error(err));
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
