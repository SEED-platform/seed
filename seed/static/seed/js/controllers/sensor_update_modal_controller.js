/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.sensor_update_modal', []).controller('sensor_update_modal_controller', [
  '$scope',
  '$state',
  '$stateParams',
  '$uibModalInstance',
  '$window',
  'uiGridConstants',
  'spinner_utility',
  'Notification',
  'organization_id',
  'view_id',
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
    Notification,
    organization_id,
    view_id,
    sensor,
    sensor_service
  ) {
    $scope.sensor = { ...sensor };

    $scope.update_sensor = () => {
      sensor_service
        .update_sensor(
          organization_id,
          view_id,
          $scope.sensor.id,
          $scope.sensor.display_name,
          $scope.sensor.location_description,
          $scope.sensor.description,
          $scope.sensor.type,
          $scope.sensor.units,
          $scope.sensor.column_name
        )
        .then(() => {
          $scope.refresh_page();
        })
        .catch((err) => {
          if (err.status === 400) {
            Notification.error(err);
          }
        });
    };

    $scope.refresh_page = () => {
      $state.reload();
      $uibModalInstance.dismiss('cancel');
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
