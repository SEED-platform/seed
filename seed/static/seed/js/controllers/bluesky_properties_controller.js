/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_properties_controller', [])
.controller('bluesky_properties_controller', [
  '$scope',
  '$routeParams',
  'properties',
  function(
    $scope,
    $routeParams,
    properties
  ) {
      $scope.tab = 'P';
      $scope.columns = [
          'jurisdiction_property_identifier',
          'lot_number',
          'property_name',
          'address_line_1',
          'energy_score',
          'site_eui'
      ];
      $scope.objects = properties;
}]);
