/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.export_report_modal', []).controller('export_report_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'axes_data',
  'cycle_start',
  'cycle_end',
  'inventory_reports_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, axes_data, cycle_start, cycle_end, inventory_reports_service) {
    $scope.export_name = '';

    $scope.export_selected = () => {
      let filename = $scope.export_name;

      if (!filename) return;

      const ext = '.xlsx';
      if (!filename.endsWith(ext)) filename += ext;

      inventory_reports_service.export_reports_data(axes_data, cycle_start, cycle_end).then((response) => {
        const blob_type = response.headers()['content-type'];

        const blob = new Blob([response.data], { type: blob_type });
        saveAs(blob, filename);

        $scope.close();
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };
  }
]);
