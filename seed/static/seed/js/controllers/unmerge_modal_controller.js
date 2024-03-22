/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.unmerge_modal', []).controller('unmerge_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'inventory_type',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, inventory_type) {
    $scope.inventory_type = inventory_type;

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
