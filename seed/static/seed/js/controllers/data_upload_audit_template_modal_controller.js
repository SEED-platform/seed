/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
    'view_id',
    'organization',
    'cycle_id',
    'upload_from_file',
    'audit_template_service',
    function (
      $scope,
      $state,
      $uibModal,
      $uibModalInstance,
      urls,
      uiGridConstants,
      spinner_utility,
      view_id,
      organization,
      cycle_id,
      upload_from_file,
      audit_template_service
    ) {
      $scope.stage = "UPLOAD_OPTIONS";
      $scope.view_id = view_id;
      $scope.organization = organization;
      $scope.organization_id = $scope.organization.id;
      $scope.cycle_id = cycle_id;
      $scope.upload_from_file = upload_from_file
      $scope.error = null;

      $scope.upload_from_file_and_close = function (event_message, file, progress) {
        $scope.close();
        $scope.upload_from_file(event_message, file, progress);
      };

      $scope.display_import_form = function () {
        $scope.stage = "IMPORT_FORM";
      };

      $scope.cancel_import_form = function () {
        $scope.stage = "UPLOAD_OPTIONS";
      };

      $scope.confirm_import = function () {
        if (!$scope.organization.at_api_token) {
          $scope.error = "INCOMPELETE_CREDENTIALS"
        } else {
          $scope.submit_request();
        }
      };

      $scope.submit_request = function () {
        $scope.stage = "AWAITING_REPONSE";
        spinner_utility.show();
        // building_xml = audit_template_service.get_building_xml(id);
        // console.log('building_xml', building_xml);
        spinner_utility.hide()
        $scope.show_results();
      };

      $scope.show_results = function () {
        $scope.stage = "CONFIRM_INCOMING_DATA";
      };

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };

      $scope.open_at_token_modal = function (org) {
        var modal = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/at_token_modal.html',
          controller: 'at_token_modal_controller',
          resolve: {
            'organization': organization,
            'audit_template_service': audit_template_service
          }
        });
        modal.result.then(function (token) {
          $scope.organization.at_api_token = token;
        });
      };

    }]);
