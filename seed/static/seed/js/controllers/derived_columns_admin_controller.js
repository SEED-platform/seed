/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.derived_columns_admin', [])
  .controller('derived_columns_admin_controller', [
    '$scope',
    '$log',
    'auth_payload',
    'organization_payload',
    'derived_columns_payload',
    function ($scope, $log, auth_payload, organization_payload, derived_columns_payload) {

      $scope.auth = auth_payload.auth;
      $scope.org = organization_payload.organization;
      $scope.derived_columns = derived_columns_payload.derived_columns;

      $scope.sort_columns = false;

      $scope.toggle_name_order_sort = function () {
        $scope.sort_columns = !$scope.sort_columns
        if ($scope.sort_columns) {
          $scope.derived_columns.sort((a, b) => (a.name > b.name) ? 1 : -1)
        } else {
          $scope.derived_columns.sort((a, b) => (a.id > b.id) ? 1 : -1)
        }
      };
    }
  ]);
