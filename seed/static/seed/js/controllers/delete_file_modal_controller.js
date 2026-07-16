/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.delete_file_modal', []).controller('delete_file_modal_controller', [
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
