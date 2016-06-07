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
  'cycles',
  function(
    $scope,
    $routeParams,
    bluesky_service,
    properties,
    cycles
  ) {
      $scope.object = 'property';

      $scope.columns = [
        'jurisdiction_property_identifier',
        'lot_number',
        'property_name',
        'address_line_1',
        'energy_score',
        'site_eui',
        // Taxlot fields
        'district'
      ];
      $scope.objects = properties.results;

      var refresh_objects = function() {
        bluesky_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function(properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
        });
      };

      $scope.cycle = {
          selected_cycle: cycles[0],
          cycles: cycles
      };
      $scope.update_cycle = function(cycle) {
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      $scope.pagination = properties.pagination;
      $scope.number_per_page_options = [10, 25, 50];
      $scope.number_per_page = $scope.number_per_page_options[0];
      $scope.update_number_per_page = function(number) {
        $scope.number_per_page = number;
        $scope.pagination.page = 1;
        refresh_objects();
      };
      $scope.pagination_first = function() {
        $scope.pagination.page = 1;
        refresh_objects();
      };
      $scope.pagination_previous = function() {
        $scope.pagination.page--;
        refresh_objects();
      };
      $scope.pagination_next = function() {
        $scope.pagination.page++;
        refresh_objects();
      };
      $scope.pagination_last = function() {
        $scope.pagination.page = $scope.pagination.num_pages;
        refresh_objects();
      };
}]);
