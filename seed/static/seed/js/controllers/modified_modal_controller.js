/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.modified_modal', []).controller('modified_modal_controller', [
  '$scope',
  '$uibModalInstance',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance) {
    $scope.leave = () => {
      $uibModalInstance.close();
    };

    $scope.stay = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
