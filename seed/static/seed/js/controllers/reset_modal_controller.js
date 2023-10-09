/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.reset_modal', []).controller('reset_modal_controller', [
  '$scope',
  '$uibModalInstance',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance) {
    $scope.reset = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
