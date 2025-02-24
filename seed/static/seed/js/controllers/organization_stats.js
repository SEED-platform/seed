/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.organization_stats', []).controller('organization_stats_controller', [
  '$scope',
  'all_columns',
  'organization_payload',
  'auth_payload',

  // eslint-disable-next-line func-names
  function ($scope, all_columns, organization_payload, auth_payload) {
    $scope.fields = all_columns.columns;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
  }

]);
