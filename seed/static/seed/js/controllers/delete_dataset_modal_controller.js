/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_dataset_modal', [])
  .controller('delete_dataset_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'dataset_service',
    'dataset',
    function ($scope, $uibModalInstance, dataset_service, dataset) {
      $scope.dataset = dataset;
      $scope.delete_dataset = function () {
        dataset_service.delete_dataset($scope.dataset.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
