/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.meter_deletion_modal', []).controller('meter_deletion_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'meter_service',
  'spinner_utility',
  'organization_id',
  'group_id',
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
    group_id,
    meter,
    view_id,
    refresh_meters_and_readings
  ) {
    $scope.meter_name = meter.alias ?? 'meter';

    $scope.delete_meter = () => {
      spinner_utility.show();
      let delete_promise;
      if (view_id) {
        delete_promise = meter_service.delete_property_meter(organization_id, meter.id, view_id);
      } else {
        delete_promise = meter_service.delete_group_meter(organization_id, meter.id, group_id);
      }
      delete_promise.then(() => {
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
