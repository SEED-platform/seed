/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.document_upload_modal', [])
  .controller('document_upload_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_id',
    'uploader_service',
    'view_id',
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_id,
      uploader_service,
      view_id,
    ) {

      $scope.step = {
        number: 1
      };

      $scope.view_id = view_id;
      $scope.organization_id = organization_id;

      $scope.uploader = {
        invalid_file_extension_alert: false,
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: ''
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

      $scope.uploaderfunc = function (event_message, file, progress) {
        switch (event_message) {
          case 'invalid_extension':
            $scope.uploader.invalid_file_extension_alert = true;
            break;

          case 'upload_submitted':
            $scope.uploader.filename = file.filename;
            $scope.uploader.invalid_file_extension_alert = false;
            $scope.uploader.in_progress = true;
            $scope.uploader.status_message = 'uploading file';
            break;

          case 'upload_error':
            $scope.uploader.status_message = 'upload failed';
            $scope.uploader.complete = false;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 0;
            alert(file.error);
            break;

          case 'upload_in_progress':
            $scope.uploader.in_progress = true;
            $scope.uploader.progress = 100 * progress.loaded / progress.total;
            break;

          case 'upload_complete':
            $scope.uploader.status_message = 'upload complete';
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 100;
            $scope.step.number = 3;
            $state.reload();
            break;
        }

        _.defer(function () {
          $scope.$apply();
        });
      };

      var saveFailure = function (error) {
        // present error message

        $scope.uploader.invalid_file_extension_alert = false;
        $scope.uploader.invalid_file_contents = true;

        // Be sure user is back to step 1 where the error is shown and they can upload another file
        $scope.step.number = 1;
      };

      var saveSuccess = function (progress_data) {
        // recheck progress in order to ensure message has been appended to progress_data
        uploader_service.check_progress(progress_data.progress_key).then(function (data) {
          $scope.uploader.status_message = 'saving complete';
          $scope.uploader.progress = 100;
          $scope.step.number = 3;
        });
      };

      $scope.refresh_page = function () {
        $state.reload();
        $uibModalInstance.dismiss('cancel');
      };

    }]);
