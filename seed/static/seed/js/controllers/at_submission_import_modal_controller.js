/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('SEED.controller.at_submission_import_modal', []).controller('at_submission_import_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'audit_template_service',
  'uploader_service',
  'org',
  'cycles',
  'view_ids',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    audit_template_service,
    uploader_service,
    org,
    cycles,
    view_ids
  ) {
    $scope.org = org;
    $scope.cycles = cycles;
    $scope.view_ids = view_ids;
    $scope.status = {
      progress: 0,
      status_message: '',
      in_progress: false,
      complete: false,
      result: {}
    };

    $scope.form_data = {
      default_cycle: null
    };

    $scope.get_submissions = () => {
      $scope.status.in_progress = true;
      audit_template_service.batch_get_city_submission_xml_and_update($scope.org.id, $scope.view_ids, $scope.form_data.default_cycle)
        .then((response) => {
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
        })
        .catch(() => handle_response('Unexpected Error.', true));
    };

    const handle_response = (message, error = false) => {
      $scope.status.in_progress = false;
      $scope.status.complete = true;
      if (error) {
        $scope.status.result.error = message;
      } else {
        $scope.status.result = message;
      }
    };

    $scope.close = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
