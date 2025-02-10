/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.service_detail', []).controller('service_detail_controller', [
  '$scope',
  '$uibModalInstance',
  '$stateParams',
  'service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, $stateParams, service) {
    console.log(service);
  }
]);
