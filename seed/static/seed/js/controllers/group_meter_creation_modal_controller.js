/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.group_meter_creation_modal', []).controller('group_meter_creation_modal_controller', [
  '$scope',
  '$stateParams',
  '$uibModalInstance',
  'inventory_group_service',
  'inventory_service',
  'meter_service',
  'spinner_utility',
  'Notification',
  'organization_id',
  'systems',
  'group_id',
  'refresh_meters_and_readings',
  'inventory_group_service',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $stateParams,
    $uibModalInstance,
    inventory_group_service,
    inventory_service,
    meter_service,
    spinner_utility,
    Notification,
    organization_id,
    systems,
    group_id,
    refresh_meters_and_readings,
    inventory_group_service,
  ) {
    $scope.systems = systems;
    $scope.types = ['Coal (anthracite)',
      'Coal (bituminous)',
      'Coke',
      'Diesel',
      'District Chilled Water',
      'District Chilled Water - Absorption',
      'District Chilled Water - Electric',
      'District Chilled Water - Engine',
      'District Chilled Water - Other',
      'District Hot Water',
      'District Steam',
      'Electric',
      'Electric - Grid',
      'Electric - Solar',
      'Electric - Wind',
      'Fuel Oil (No. 1)',
      'Fuel Oil (No. 2)',
      'Fuel Oil (No. 4)',
      'Fuel Oil (No. 5 and No. 6)',
      'Kerosene',
      'Natural Gas',
      'Other:',
      'Propane',
      'Wood',
      'Cost',
      'Electric - Unknown',
      'Custom Meter',
      'Potable Indoor',
      'Potable Outdoor',
      'Potable: Mixed Indoor/Outdoor',
    ];

    $scope.meter = {}

    $scope.$watchCollection('meter', () => {
      $scope.form_valid = (
        $scope.meter.type !== undefined &&
        $scope.meter.alias !== undefined &&
        $scope.meter.system_id !== undefined
      )
    });

    $scope.create_meter = () => {
      inventory_group_service.create_group_meter(group_id, $scope.meter).then((response) => {
        if (response.status === 200) {
          Notification.info('Meter created! Click on the pencil icon next to your meter to further configure its connections.');
          refresh_meters_and_readings();
          spinner_utility.show();
          $uibModalInstance.dismiss('cancel');
        } else {
          $scope.error = response.data.message;
        }
      });
    };
  }
]);
