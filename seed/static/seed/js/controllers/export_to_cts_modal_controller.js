/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.export_to_CTS_modal', []).controller('export_to_CTS_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'ids',
  'org_id',
  'inventory_service',
  'uploader_service',
  // eslint-disable-next-line func-names
  function ($scope, $state, $uibModalInstance, ids, org_id, inventory_service, uploader_service) {
    $scope.ids = ids;
    $scope.org_id = org_id;
    $scope.step = { number: 0 };
    $scope.uploader = {
      invalid_extension_alert: false,
      invalid_geojson_extension_alert: false,
      invalid_xml_extension_alert: false,
      invalid_xml_zip_extension_alert: false,
      in_progress: false,
      progress: 0,
      complete: false,
      status_message: '',
      progress_last_updated: null,
      progress_last_checked: null
    };

    $scope.export = () => {
      const property_view_ids = { property_view_ids: ids };
      inventory_service.batch_export_to_cts($scope.org_id, property_view_ids).then((response) => {
        const blob_type = response.headers()['content-type'];
        data = response.data;
        const blob = new Blob([data], { type: blob_type });

        saveAs(blob, "hey.xlsx");

        $scope.close();
        return response.data;
      });
    };

    $scope.cancel = (reload = false) => {
      $uibModalInstance.close({});
      if (reload) $state.reload();
    };
  }
]);
