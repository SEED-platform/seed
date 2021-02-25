/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_column_modal', [])
  .controller('delete_column_modal_controller', [
    '$scope',
    '$window',
    '$log',
    '$uibModalInstance',
    'spinner_utility',
    'columns_service',
    'uploader_service',
    'organization_id',
    'column',
    function ($scope, $window, $log, $uibModalInstance, spinner_utility, columns_service, uploader_service, organization_id, column) {
      $scope.column_name = column.column_name;

      $scope.progressBar = {
        progress: 0
      }

      $scope.delete = function () {
        $scope.state = 'running';
        columns_service.delete_column_for_org(organization_id, column.id).then(function (data) {
          // $scope.result = result.data.message;
          // $scope.state = 'done';
          uploader_service.check_progress_loop(data.progress_key, 0, 1, function () {
            console.log('DONE', $scope.progressBar);
            $scope.result = $scope.progressBar.status_message;
            $scope.state = 'done';
          }, function () {
            // Do nothing
          }, $scope.progressBar);
        }).catch(function (err) {
          $log.error(err);
          $scope.result = 'Failed to delete column';
          $scope.state = 'done';
        });
      };

      $scope.refresh = function () {
        spinner_utility.show();
        $window.location.reload();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
