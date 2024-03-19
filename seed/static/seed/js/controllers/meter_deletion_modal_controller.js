/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.meter_deletion_modal', []).controller('meter_deletion_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'meter_service',
  'spinner_utility',
  'organization_id',
  'meter',
  'view_id',
  'refresh_meters_and_readings',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    meter_service,
    spinner_utility,
    organization_id,
    meter,
    view_id,
    refresh_meters_and_readings
  ) {
    $scope.meter_name = meter.alias ?? 'meter';

    $scope.delete_meter = () => {
      spinner_utility.show();
      meter_service.delete_meter(organization_id, view_id, meter.id).then(() => {
        refresh_meters_and_readings();
        spinner_utility.show();
        $uibModalInstance.dismiss('cancel');
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };
  }
]);
