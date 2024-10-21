/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.meter_edit_modal', []).controller('meter_edit_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'inventory_group_service',
  'meter_service',
  'spinner_utility',
  'organization_id',
  'meter',
  'property_id',
  'view_id',
  'refresh_meters_and_readings',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    inventory_group_service,
    meter_service,
    spinner_utility,
    organization_id,
    meter,
    property_id,
    view_id,
    refresh_meters_and_readings
  ) {
    $scope.selectedGroup = null;
    $scope.selectedSystem = null;
    $scope.selectedService = null;

    $scope.potentialGroups = null;
    $scope.potentialSystems = null;
    $scope.potentialServices = null;

    inventory_group_service.get_groups_for_inventory("properties", [property_id], include_systems=true).then((groups) => {
      $scope.potentialGroups = groups;
    });

    $scope.selectGroup = () => {$scope.potentialSystems = $scope.selectedGroup.systems};
    $scope.selectSystem = () => {$scope.potentialServices = $scope.selectedSystem.services};

    $scope.update_meter = () => {
      meter_service.update_meter_connection(organization_id, view_id, meter.id, $scope.selectedService?.id).then(() => {
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
