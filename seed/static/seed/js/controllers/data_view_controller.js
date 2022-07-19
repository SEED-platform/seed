/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_view', [])
  .controller('data_view_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'inventory_service',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      inventory_service,
      cycles_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data_view = 0;

      $scope.data_views = [
        { 'id': 1, 'name': 'Data View One' },
        { 'id': 2, 'name': 'Data View Two' },
        { 'id': 3, 'name': 'Data View Three' }
      ];

      $scope.select_data_view = function () {
        console.log($scope.data_view);
      };
    }

  ]);
