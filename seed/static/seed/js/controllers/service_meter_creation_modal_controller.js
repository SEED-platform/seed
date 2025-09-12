/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.service_meter_creation_modal', []).controller('service_meter_creation_modal_controller', [
  '$scope',
  '$stateParams',
  'properties',
  'organization_id',
  'service_service',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $stateParams,
    properties,
    organization_id,
    service_service,
  ) {
      $scope.group_id = $stateParams.group_id;
      $scope.system_id = $stateParams.system_id;
      $scope.service_id = $stateParams.service_id;

      $scope.direction = 'imported';
      $scope.direction_options = [
        { display: 'Imported', value: 'imported' },
        { display: 'Exported', value: 'exported' }
      ];

      $scope.type = '';
      $scope.types = [
        'Coal (anthracite)',
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
        'Other',
        'Propane',
        'Wood',
        'Cost',
        'Electric - Unknown',
        'Custom Meter',
        'Potable Indoor',
        'Potable Outdoor',
        'Potable: Mixed Indoor/Outdoor'
      ];

      $scope.properties = properties;
      $scope.selected_property_indices = [];
      $scope.unselected_property_indices = [...Array(properties.length).keys()];

      $scope.select_property = (index) => {
        $scope.selected_property_indices.push(index);
        $scope.unselected_property_indices = $scope.unselected_property_indices.filter(i => i !== index)
      };

      $scope.unselect_property = (index) => {
        $scope.unselected_property_indices.push(index);
        $scope.selected_property_indices = $scope.selected_property_indices.filter(i => i !== index)
      };

      $scope.create_meters = () => {
        service_service.create_meters(organization_id, $scope.group_id, $scope.system_id, $scope.service_id, {
          direction: $scope.direction,
          type: $scope.type,
          property_ids: properties.filter((_, i) => $scope.selected_property_indices.includes(i)).map(p => p.property_id),
        })
      }
  }
]);
