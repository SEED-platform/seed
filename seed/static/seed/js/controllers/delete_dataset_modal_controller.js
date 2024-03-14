/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_dataset_modal', []).controller('delete_dataset_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'dataset_service',
  'dataset',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, dataset_service, dataset) {
    $scope.dataset = dataset;
    $scope.delete_dataset = () => {
      dataset_service.delete_dataset($scope.dataset.id).then(() => {
        $uibModalInstance.close();
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
