/*
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.analyses', [])
  .controller('analyses_controller', [
    '$scope',
    'organization_payload',
    'auth_payload',
    function (
      $scope, 
      organization_payload,
      auth_payload
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
    }
  ]);
