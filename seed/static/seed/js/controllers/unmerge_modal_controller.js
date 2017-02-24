/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.unmerge_modal', [])
  .controller('unmerge_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'inventory_type',
    function ($scope, $uibModalInstance, inventory_type) {
      $scope.inventory_type = inventory_type;

      $scope.close = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
