/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_report_modal', []).controller('export_report_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'axes_data',
  'cycle_start',
  'cycle_end',
  'inventory_reports_service',
  function (
    $scope,
    $uibModalInstance,
    axes_data,
    cycle_start,
    cycle_end,
    inventory_reports_service
  ) {
    $scope.export_name = '';

    $scope.export_selected = function () {
      var filename = $scope.export_name;

      var ext = '.xlsx';
      if (!_.endsWith(filename, ext)) filename += ext;

      inventory_reports_service.export_reports_data(axes_data, cycle_start, cycle_end)
        .then(function (response) {
          var blob_type = response.headers()['content-type'];

          var blob = new Blob([response.data], {type: blob_type});
          saveAs(blob, filename);

          $scope.close();
        });
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = function () {
      $uibModalInstance.close();
    };
  }]);
