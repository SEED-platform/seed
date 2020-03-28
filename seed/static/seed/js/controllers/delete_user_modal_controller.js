/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_user_modal', [])
  .controller('delete_user_modal_controller', [
    '$scope',
    '$q',
    '$uibModalInstance',
    'user',
    function ($scope, $q, $uibModalInstance, user) {
      $scope.user = user;

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };

      $scope.close = function () {
        $uibModalInstance.close();
      };
    }]);
