/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.reset_modal', [])
  .controller('reset_modal_controller', [
    '$rootScope',
    '$scope',
    '$uibModalInstance',
    function ($rootScope, $scope, $uibModalInstance) {
      $scope.reset = function () {
        $rootScope.$broadcast('reset_all_rules');
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
