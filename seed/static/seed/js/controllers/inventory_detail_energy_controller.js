angular.module('BE.seed.controller.inventory_detail_energy', [])
  .controller('inventory_detail_energy_controller', [
    '$state',
    '$scope',
    '$stateParams',
    'user_service',
    'spinner_utility',
    'inventory_payload',
    function (
      $state,
      $scope,
      $stateParams,
      user_service,
      spinner_utility,
      inventory_payload,
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();

      $scope.inventory = {
        view_id: $stateParams.view_id,
        related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties,
        is_property: true,
      };
      // debugger;
    }]);
