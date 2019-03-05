angular.module('BE.seed.controller.inventory_detail_energy', [])
  .controller('inventory_detail_energy_controller', [
    '$state',
    '$scope',
    '$stateParams',
    'property_energy_usage',
    'spinner_utility',
    'user_service',
    function (
      $state,
      $scope,
      $stateParams,
      property_energy_usage,
      spinner_utility,
      user_service,
    ) {
      spinner_utility.show();

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();

      $scope.inventory = {
        view_id: $stateParams.view_id,
      };

      $scope.data = property_energy_usage.readings;
      $scope.has_meters = $scope.data.length > 0;

      $scope.gridOptions = {
        data: 'data',
        columnDefs: property_energy_usage.headers,
      };
    }]);
