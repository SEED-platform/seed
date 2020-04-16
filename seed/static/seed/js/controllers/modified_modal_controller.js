/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.modified_modal', [])
  .controller('modified_modal_controller', [
    '$rootScope',
    '$scope',
    '$uibModalInstance',
    function ($rootScope, $scope, $uibModalInstance) {
      $scope.leave = function () {
        $rootScope.stay_on_page = false;
        $uibModalInstance.close();
      };

      $scope.stay = function () {
        $rootScope.stay_on_page = true;
        $uibModalInstance.dismiss();
      };
    }]);
