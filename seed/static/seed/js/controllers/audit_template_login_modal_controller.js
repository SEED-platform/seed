/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.audit_template_login_modal', [])
  .controller('audit_template_login_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'uiGridConstants',
    'spinner_utility',
    'view_id',
    'organization_id',
    'cycle_id',
    'upload_from_file',
    function (
      $scope,
      $state,
      $uibModalInstance,
      uiGridConstants,
      spinner_utility,
      view_id,
      organization_id,
      cycle_id,
      upload_from_file,
    ) {
      $scope.audit_template_login = {
        username: "",
        password: "",
      };
      $scope.stage = "UPLOAD_OPTIONS";
      $scope.view_id = view_id;
      $scope.organization_id = organization_id;
      $scope.cycle_id = cycle_id;
      $scope.upload_from_file = upload_from_file
      $scope.error = null;

      $scope.upload_from_file_and_close = function (event_message, file, progress) {
        $scope.close();
        $scope.upload_from_file(event_message, file, progress);
      };

      $scope.display_credentials_form = function () {
        $scope.stage = "CREDENTIAL_FORM";
      }

      $scope.confirm_credentials = function () {
        if (
          $scope.audit_template_login.username == "" ||
          $scope.audit_template_login.username == ""
        ) {
          $scope.error = "INCOMPELETE_CREDENTIALS"
        } else {
          $scope.submit_request();
        }
      };

      $scope.submit_request = function () {
        $scope.stage = "AWAITING_REPONSE";

        spinner_utility.show();

        spinner_utility.hide()
        $scope.show_results();
      }

      $scope.show_results = function () {
        $scope.stage = "CONFIRM_INCOMING_DATA";
      }

      $scope.close = function () {
        $uibModalInstance.dismiss();
      }
    }]);
