/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_upload_espm_modal', [])
  .controller('data_upload_espm_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'spinner_utility',
    'organization',
    'cycle_id',
    'upload_from_file',
    'espm_service',
    'view_id',
    'pm_property_id',
    function (
      $scope,
      $uibModalInstance,
      spinner_utility,
      organization,
      cycle_id,
      upload_from_file,
      espm_service,
      view_id,
      pm_property_id
    ) {
      $scope.organization = organization;
      $scope.view_id = view_id;
      $scope.cycle_id = cycle_id;
      $scope.upload_from_file = upload_from_file;
      $scope.error = '';
      $scope.busy = false;
      $scope.fields = {
        'pm_property_id': pm_property_id,
        'espm_username': '',
        'espm_password': ''
      };

      // password field
      $scope.secret = 'password';
      $scope.toggle_secret = function () {
        $scope.secret = ($scope.secret == 'password') ? 'text' : 'password';
      };

      $scope.upload_from_file_and_close = function (event_message, file, progress) {
        $scope.close();
        $scope.upload_from_file(event_message, file, progress);
      };

      $scope.confirm_import = function () {
        if (!$scope.fields.pm_property_id) {
          $scope.error = "An ESPM Property ID is required.";
        } else {
          $scope.submit_request();
        }
      };

      $scope.submit_request = function () {
        $scope.error = '';
        $scope.busy = true;
        spinner_utility.show();
        return espm_service.get_espm_building_xlsx($scope.organization.id, $scope.fields.pm_property_id, $scope.fields.espm_username, $scope.fields.espm_password).then(file_result => {
          spinner_utility.hide();
          if (typeof (result) == 'object' && !result.success) {
            $scope.error = 'Error: ' + result.message;
            $scope.busy = false;
          } else {
            return espm_service.update_building_with_espm_xlsx($scope.organization.id, $scope.cycle_id, $scope.view_id, file_result).then(result => {
              if (typeof (result) == 'object' && !result.success) {
                $scope.error = 'Error: ' + result.message;
                $scope.busy = false;
              } else {
                $scope.close();
                $scope.upload_from_file('upload_complete', null, null)
                $scope.busy = false;
              }
            });
          }
        });
      };

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };
    }]);
