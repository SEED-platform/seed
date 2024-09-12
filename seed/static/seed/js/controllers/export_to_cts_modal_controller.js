/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.export_to_cts_modal', []).controller('export_to_cts_modal_controller', [
  '$http',
  '$scope',
  '$state',
  '$uibModalInstance',
  'user_service',
  'ids',
  'org_id',
  'inventory_service',
  // eslint-disable-next-line func-names
  function ($http, $scope, $state, $uibModalInstance, user_service, ids, org_id, inventory_service) {
    $scope.exporting = false;

    /**
<<<<<<< HEAD
     * @type {'template' | 'femp' | null}
=======
     * @type {'evaluation_template' | 'facility_bps_template' | null}
>>>>>>> 13eeec365dfffb8bc2a36455e8c247a906d009b1
     */
    $scope.export_selection = null;
    $scope.set_selection = (selection) => {
      $scope.export_selection = selection;
    };

    $scope.set_name = (name) => {
      $scope.export_name = name;
    };

    $scope.export = () => {
      let filename = $scope.export_name;
      if (!filename.endsWith('.xlsx')) filename += '.xlsx';
      $scope.exporting = true;

      if ($scope.export_selection === 'evaluation_template') {
        inventory_service.evaluation_export_to_cts(ids).then((data) => {
          const blob_type = data.headers()['content-type'];
          const blob = new Blob([data.data], { type: blob_type });
          saveAs(blob, filename);
          $scope.close();
        });
      } else if ($scope.export_selection === 'facility_bps_template') {
        inventory_service.facility_bps_export_to_cts(org_id, { property_view_ids: ids }).then((data) => {
          const blob_type = data.headers()['content-type'];
          const blob = new Blob([data.data], { type: blob_type });
          saveAs(blob, filename);
          $scope.close();
        });
      }
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };
  }
]);
