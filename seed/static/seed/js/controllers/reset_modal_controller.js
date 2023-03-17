/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.reset_modal', [])
  .controller('reset_modal_controller', [
    '$scope',
    '$uibModalInstance',
    function ($scope, $uibModalInstance) {
      $scope.reset = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
