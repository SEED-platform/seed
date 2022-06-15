/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_plots', [])
  .controller('inventory_plots_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
    }
  ]);
