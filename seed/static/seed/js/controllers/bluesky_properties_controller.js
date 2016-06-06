/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_properties_controller', [])
.controller('bluesky_properties_controller', [
  '$scope',
  '$routeParams',
  'bluesky_service',
  'properties',
  function(
    $scope,
    $routeParams,
    bluesky_service,
    properties
  ) {
      $scope.object = 'property';

      $scope.columns = [
        'jurisdiction_property_identifier',
        'lot_number',
        'property_name',
        'address_line_1',
        'energy_score',
        'site_eui'
      ];
      $scope.objects = properties.results;
      $scope.pagination = properties.pagination;

      $scope.number_per_page_options = [1, 2, 5];
      $scope.number_per_page = 1;
      $scope.page = 1;
      $scope.update_number_per_page = function(number) {
        $scope.number_per_page = number;
        bluesky_service.get_properties(1, number).then(function(properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
        });
      }
}]);
