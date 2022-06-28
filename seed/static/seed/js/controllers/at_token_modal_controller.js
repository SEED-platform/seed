/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the Audit Template token modal.
 */
angular.module('BE.seed.controller.at_token_modal', []).controller('at_token_modal_controller', [
  '$scope',
  '$log',
  '$uibModalInstance',
  'Notification',
  'audit_template_service',
  'organization',
  function (
    $scope,
    $log,
    $uibModalInstance,
    Notification,
    audit_template_service,
    organization
  ) {
    $scope.org = organization;
    $scope.waiting_for_server = false;
    $scope.fields = {
      org_token: $scope.org.at_organization_token,
      email: null,
      password: null
    };

    $scope.submitForm = function (form) {
      if (form.$invalid) {
        return;
      }
      $scope.waiting_for_server = true;
      return audit_template_service.get_api_token(
        $scope.org.id, $scope.fields.org_token, $scope.fields.email, $scope.fields.password
      ).then(result => {
        if (result.success) {
          Notification.primary('Audit Template API Token generated.');
          $uibModalInstance.close(result.data);
        } else {
          Notification.error('Failed to generate Audit Template API Token: ' + result.message);
          $log.error('Failed to generate Audit Template API Token.', result.message);
        }
        $scope.waiting_for_server = false;
      });
    };

    $scope.cancel = function () {
      //don't do anything, just close modal.
      $uibModalInstance.dismiss('cancel');
    };

  }]);
