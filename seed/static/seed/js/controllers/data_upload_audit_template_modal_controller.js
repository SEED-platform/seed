/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.data_upload_audit_template_modal', []).controller('data_upload_audit_template_modal_controller', [
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
  'custom_id_1',
  'organization_service',
  'view_id',
  // eslint-disable-next-line func-names
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
    custom_id_1,
    organization_service,
    view_id
  ) {
    $scope.organization = organization;
    $scope.view_id = view_id;
    $scope.cycle_id = cycle_id;
    $scope.upload_from_file = upload_from_file;
    $scope.error = '';
    $scope.busy = false;
    $scope.fields = {
      custom_id_1
    };
    const city_id = $scope.organization.audit_template_city_id

    $scope.upload_from_file_and_close = (event_message, file, progress) => {
      $scope.close();
      $scope.upload_from_file(event_message, file, progress);
    };

    $scope.confirm_import = () => {
      if (!$scope.fields.custom_id_1) {
        $scope.error = 'A Custom ID 1 is required.';
      } else if (!city_id) {
        $scope.error = 'Organization city id must be set in Organization Settings'
      } else {
        $scope.submit_request();
      }
    };

    $scope.submit_request = () => {
      $scope.error = '';
      $scope.busy = true;
      spinner_utility.show();
      return audit_template_service.get_city_submission_xml_and_update($scope.organization.id, city_id, $scope.fields.custom_id_1).then((result) => {
        spinner_utility.hide();
        if (typeof result === 'object' && result.status !== 200) {
          $scope.error = `Error: ${result.message}`;
          $scope.busy = false;
        } else {
          $scope.close();
          $scope.upload_from_file('upload_complete', null, null);
          $scope.busy = false;
        }
      });
    };

    $scope.close = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
