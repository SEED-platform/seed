/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
