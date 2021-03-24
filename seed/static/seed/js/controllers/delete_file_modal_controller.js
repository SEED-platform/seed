/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_file_modal', [])
  .controller('delete_file_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'dataset_service',
    'file',
    function ($scope, $uibModalInstance, dataset_service, file) {
      $scope.file = file;
      $scope.delete_file = function () {
        dataset_service.delete_file($scope.file.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
