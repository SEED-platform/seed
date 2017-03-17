/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.organization_settings', []).controller('organization_settings_controller', [
  '$scope',
  'organization_payload',
  'auth_payload',
  'organization_service',
  function ($scope,
            organization_payload,
            auth_payload,
            organization_service) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.org_static = angular.copy($scope.org);

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.settings_updated = false;
      organization_service.save_org_settings($scope.org).then(function (data) {
        $scope.settings_updated = true;
        $scope.org_static = angular.copy($scope.org);
        $scope.$emit('organization_list_updated');
        // $scope.$emit('app_error', data);
      });
    };
  }]);
