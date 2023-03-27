/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_upload_audit_template_modal', [])
  .controller('data_upload_audit_template_modal_controller', [
    '$scope',
    '$state',
    '$uibModal',
    '$uibModalInstance',
    'urls',
    'uiGridConstants',
    'spinner_utility',
    'organization',
    'cycle_id',
    'upload_from_file',
    'audit_template_service',
    'organization_service',
    'audit_template_building_id',
    'view_id',
    function (
      $scope,
      $state,
      $uibModal,
      $uibModalInstance,
      urls,
      uiGridConstants,
      spinner_utility,
      organization,
      cycle_id,
      upload_from_file,
      audit_template_service,
      organization_service,
      audit_template_building_id,
      view_id
    ) {
      $scope.organization = organization;
      $scope.view_id = view_id;
      $scope.cycle_id = cycle_id;
      $scope.upload_from_file = upload_from_file;
      $scope.error = '';
      $scope.busy = false;
      $scope.fields = {
        'audit_template_building_id': audit_template_building_id
      };

      $scope.upload_from_file_and_close = function (event_message, file, progress) {
        $scope.close();
        $scope.upload_from_file(event_message, file, progress);
      };

      $scope.confirm_import = function () {
        if (!$scope.fields.audit_template_building_id) {
          $scope.error = "An Audit Template building ID is required.";
        } else {
          $scope.submit_request();
        }
      };

      $scope.submit_request = function () {
        $scope.error = '';
        $scope.busy = true;
        spinner_utility.show();
        return audit_template_service.get_building_xml($scope.organization.id, $scope.fields.audit_template_building_id).then(result => {
          spinner_utility.hide();
          if (typeof(result) == 'object' && !result.success) {
            $scope.error = 'Error: ' + result.message
            $scope.busy = false;
          } else {
            return audit_template_service.update_building_with_xml($scope.organization.id, $scope.cycle_id, $scope.view_id, result).then(result => {
              $scope.close();
              $scope.upload_from_file('upload_complete', null, null)
              $scope.busy = false;
            });
          }
        });
      };

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };

    }]);
