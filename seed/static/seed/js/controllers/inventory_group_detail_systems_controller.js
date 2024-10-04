/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_detail_systems', [])
  .controller('inventory_group_detail_systems_controller', [
    '$scope',
    '$state',
    '$stateParams',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
    }]);
