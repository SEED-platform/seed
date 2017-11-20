/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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

    var $translate = { instant: _.identity }; // stub in for later

    $scope.org_static = angular.copy($scope.org);

    $scope.unit_options_eui = [
      { label: $translate.instant('kBtu/sq. ft./year'), value: 'kBtu/ft**2/year' },
      { label: $translate.instant('GJ/m²/year'), value: 'GJ/m**2/year' },
      { label: $translate.instant('MJ/m²/year'), value: 'MJ/m**2/year' },
      { label: $translate.instant('kWh/m²/year'), value: 'kWh/m**2/year' },
      { label: $translate.instant('kBtu/m²/year'), value: 'kBtu/m**2/year' }
    ];

    $scope.unit_options_area = [
      { label: $translate.instant('square feet'), value: 'ft**2' },
      { label: $translate.instant('square metres'), value: 'm**2' }
    ];

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.settings_updated = false;
      organization_service.save_org_settings($scope.org).then(function () {
        $scope.settings_updated = true;
        $scope.org_static = angular.copy($scope.org);
        $scope.$emit('organization_list_updated');
        // $scope.$emit('app_error', data);
      });
    };
  }]);
