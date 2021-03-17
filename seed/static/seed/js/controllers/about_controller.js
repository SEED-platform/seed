/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.about', [])
  .controller('about_controller', [
    '$scope',
    'version_payload',
    function (
      $scope,
      version_payload
    ) {
      $scope.version = version_payload.version;
      $scope.sha = version_payload.sha;
    }]);
