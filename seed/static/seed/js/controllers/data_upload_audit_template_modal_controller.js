/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.data_upload_audit_template_modal', []).controller('data_upload_audit_template_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'Notification',
  'spinner_utility',
  'uploader_service',
  'organization',
  'cycle_id',
  'upload_from_file',
  'audit_template_service',
  'custom_id_1',
  'view_id',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    Notification,
    spinner_utility,
    uploader_service,
    organization,
    cycle_id,
    upload_from_file,
    audit_template_service,
    custom_id_1,
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
    const city_id = $scope.organization.audit_template_city_id;
    $scope.status = {};

    $scope.upload_from_file_and_close = (event_message, file, progress) => {
      $scope.close();
      $scope.upload_from_file(event_message, file, progress);
    };

    $scope.confirm_import = () => {
      if (!$scope.fields.custom_id_1) {
        $scope.error = 'A Custom ID 1 is required.';
      } else if (!city_id) {
        $scope.error = 'Organization city id must be set in Organization Settings';
      } else {
        $scope.submit_request();
      }
    };

    const handle_response = (message, error = false) => {
      spinner_utility.hide();
      if (error) {
        Notification.error(message);
        $scope.close();
      } else {
        Notification.success('Successfully updated property');
        $scope.close(true);
      }
      spinner_utility.hide();
    };

    $scope.submit_request = () => {
      $scope.error = '';
      $scope.busy = true;
      spinner_utility.show();
      return audit_template_service.get_city_submission_xml_and_update($scope.organization.id, city_id, $scope.fields.custom_id_1).then((response) => {
        const data = response.data;
        if (response.status !== 200) {
          handle_response(data.message, true);
        } else {
          uploader_service.check_progress_loop(
            data.progress_key,
            0,
            1,
            (data) => handle_response(data.message),
            (data) => handle_response(data.data.message, true),
            $scope.status
          );
        }
      });
    };

    $scope.close = (reload = false) => {
      $uibModalInstance.dismiss();
      if (reload) $state.reload();
    };
  }
]);
