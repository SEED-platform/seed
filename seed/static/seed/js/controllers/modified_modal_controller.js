/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.modified_modal', [])
  .controller('modified_modal_controller', [
    '$scope',
    '$uibModalInstance',
    function ($scope, $uibModalInstance) {
      $scope.leave = function () {
        $uibModalInstance.close();
      };

      $scope.stay = function () {
        $uibModalInstance.dismiss();
      };
    }]);
