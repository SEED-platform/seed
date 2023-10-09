/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.export_to_audit_template_modal', []).controller('export_to_audit_template_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'ids',
  'org_id',
  'audit_template_service',
  'uploader_service',
  ($scope, $state, $uibModalInstance, ids, org_id, audit_template_service, uploader_service) => {
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
      audit_template_service.batch_export_to_audit_template($scope.org_id, property_view_ids).then((response) => {
        $scope.step.number = 1;
        progress_key = response.progress_key;

        uploader_service.check_progress_loop(
          progress_key,
          0,
          1,
          function (summary) {
            $scope.upload_summary = summary.message;
            $scope.step.number = 2;
          },
          function () {
            // do nothing
          },
          $scope.uploader
        );
      });
    };

    $scope.cancel = (reload = false) => {
      $uibModalInstance.close({});
      if (reload) $state.reload();
    };
  }
]);
