/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_taxlots_controller', [])
.controller('bluesky_taxlots_controller', [
  '$scope',
  '$routeParams',
  'taxlots',
  function(
    $scope,
    $routeParams,
    taxlots
  ) {
      $scope.tab = 'T';
      $scope.columns = [
          'jurisdiction_taxlot_identifier',
          'block_number',
          'district',
          'address'
      ];
      $scope.objects = taxlots;
}]);
