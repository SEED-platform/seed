angular.module('BE.seed.controller.inventory_detail_energy', [])
  .controller('inventory_detail_energy_controller', [
    '$state',
    '$scope',
    '$stateParams',
    'energy_service',
    'property_energy_usage',
    'spinner_utility',
    'user_service',
    function (
      $state,
      $scope,
      $stateParams,
      energy_service,
      property_energy_usage,
      spinner_utility,
      user_service
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

      $scope.interval = {
        options: [ // TODO: Translate this
          'Exact',
          'Month',
        ],
        selected: 'Exact',
      };

      $scope.update_interval = function(selected_interval) {
        spinner_utility.show();
        $scope.interval.selected = selected_interval;
        energy_service.property_energy_usage($scope.inventory.view_id, $scope.organization.id, selected_interval).then(function(usage) {
          $scope.data = usage.readings;
          $scope.gridOptions.columnDefs = usage.headers;
          $scope.has_meters = $scope.data.length > 0;
          spinner_utility.hide();
        });
      };
    }]);
