/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
  '$scope', '$uibModalInstance', 'gridApi', 'uiGridExporterConstants', function ($scope, $uibModalInstance, gridApi, uiGridExporterConstants) {
    $scope.gridApi = gridApi;
    $scope.export_name = '';
    $scope.export_type = 'csv';

    $scope.export_selected = function () {
      var filename = $scope.export_name,
        ext = '.' + $scope.export_type;
      if (!_.endsWith(filename, ext)) filename += ext;
      $scope.gridApi.grid.options.exporterCsvFilename = filename;
      $scope.gridApi.exporter.csvExport(uiGridExporterConstants.SELECTED, uiGridExporterConstants.VISIBLE);
      $uibModalInstance.close();
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = function () {
      $uibModalInstance.close();
    };
  }]);
