/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
