/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.inventory_detail_ubid', []).controller('inventory_detail_ubid_controller', [
  '$scope',
  '$stateParams',
  'organization_service',
  'inventory_payload',
  'organization_payload',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, organization_service, inventory_payload, organization_payload) {
    $scope.item_state = inventory_payload.state;
    $scope.organization = organization_payload.organization;
    $scope.inventory_payload = inventory_payload;
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.reload = false;

    // for nav
    $scope.inventory = { view_id: $stateParams.view_id };

    $scope.inventory_display_name = organization_service.get_inventory_display_value($scope.organization, $scope.inventory_type === 'properties' ? 'property' : 'taxlot', $scope.item_state);

    $scope.$on('reload', () => {
      // pass to the map controller
      $scope.reload = true;
    });
  }
]);
