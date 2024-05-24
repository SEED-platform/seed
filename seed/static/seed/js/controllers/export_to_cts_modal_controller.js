/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.export_to_cts_modal', []).controller('export_to_cts_modal_controller', [
  '$http',
  '$scope',
  '$state',
  '$uibModalInstance',
  'user_service',
  'ids',
  'org_id',
  'inventory_service',
  'uploader_service',
  // eslint-disable-next-line func-names
  function ($http, $scope, $state, $uibModalInstance, user_service, ids, org_id, inventory_service, uploader_service) {
    $scope.ids = ids;
    $scope.org_id = org_id;
    $scope.exporting = false;


    $scope.export = () => {
      let filename = $scope.export_name;
      if (!filename.endsWith(".xlsx")) filename += ".xlsx";
      $scope.exporting = true;

      $http.get('/api/v3/tax_lot_properties/start_export_to_cts/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((data) => {
        uploader_service.check_progress_loop(
          data.data.progress_key,
          0,
          1,
          () => {},
          () => {},
          $scope.exporter_progress
        );
        return inventory_service.export_to_cts(property_view_ids=ids).then((data) => {
          const blob_type = data.headers()['content-type']
          const blob = new Blob([data.data], { type: blob_type });
          saveAs(blob, filename);
          $scope.close();

        });
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
