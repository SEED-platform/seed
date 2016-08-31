/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_settings', [])
  .controller('inventory_detail_settings_controller', [
    '$scope',
    '$uibModalInstance',
    '$state',
    '$stateParams',
    function ($scope, $uibModalInstance, $state, $stateParams) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id
      };
      $scope.cycle = {
        id: $stateParams.cycle_id
      };
    }]);
