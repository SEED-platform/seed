/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_file_modal', []).controller('delete_file_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'dataset_service',
  'file',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, dataset_service, file) {
    $scope.file = file;
    $scope.delete_file = () => {
      dataset_service.delete_file($scope.file.id).then(() => {
        $uibModalInstance.close();
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
