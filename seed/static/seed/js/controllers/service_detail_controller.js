/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.service_detail', []).controller('service_detail_controller', [
  '$scope',
  '$stateParams',
  'service',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, service) {
    $scope.group_id = $stateParams.group_id;
    $scope.system_id = $stateParams.system_id;
    $scope.service_id = $stateParams.service_id;
    $scope.inventory_type = $stateParams.inventory_type;

    $scope.service = service;

    $scope.headers = ["Property", "Connected Via", "Connection Type", "Meter Data?"];
  }
]);
