/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
