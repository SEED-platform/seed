/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.at_submission_import_modal', []).controller('at_submission_import_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'audit_template_service',
  'uploader_service',
  'org',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $uibModalInstance,
    audit_template_service,
    uploader_service,
    org,
    ) {
      $scope.org = org
      $scope.test = 'dog'
      $scope.status = {
        progress: 0,
        status_message: '',
        in_progress: false,
        complete: false,
        result: 'error' // default to error
      };
      // $scope.org = organization

      $scope.get_submissions = () => {
        console.log('modal get')
        console.log($scope.org.audit_template_city_id)
        $scope.status.in_progress = true,
        audit_template_service.batch_get_city_submission_xml_and_update($scope.org.id, $scope.org.audit_template_city_id)
          .then(response => {
            console.log('>>> part 1')
            data = response.data
            uploader_service.check_progress_loop(
              data.progress_key,
              0,
              1,
              (data) => {
                $scope.status.in_progress = false
                $scope.status.complete = true
                $scope.status.result = data.message
              },
              () => {
                $scope.status.in_progress = false
                $scope.status.complete = true
                console.log('fail')
              },
              $scope.status)
        })
      }

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };

  }
]);
