/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_detail_dashboard', [])
  .controller('inventory_group_detail_dashboard_controller', [
    '$scope',
    '$state',
    '$stateParams',
    'cycles',
    'group',
    'inventory_group_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      cycles,
      group,
      inventory_group_service
    ) {
      $scope.inventory_display_name = group.name;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.cycles = cycles.cycles;
      $scope.selectedCycle = $scope.cycles[0] ?? undefined;
      $scope.data = {};
      inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id).then((data) => { $scope.data = data; });

      $scope.changeCycle = () => {
        inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id).then((data) => { $scope.data = data; });
      };
    }]);
