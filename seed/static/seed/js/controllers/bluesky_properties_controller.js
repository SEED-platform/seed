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
        'building_portfolio_manager_identifier',
        'jurisdiction_property_identifier',
        'jurisdiction_tax_lot_identifier',
        'primary',
        'address',
        'address_line_1',
        'city',
        'property_name',
        'campus',
        //'PM Parent Property ID',
        'gross_floor_area',
        'use_description',
        'energy_score',
        'site_eui',
        'property_notes',
        'year_ending',
        'owner',
        'owner_email',
        'owner_telephone',
        'generation date',
        'release_date',
        'address_line_2',
        'state',
        'postal_code',
        'building_count',
        'year_built',
        'recent_sale_date',
        'conditioned_floor_area',
        'occupied_floor_area',
        'owner_address',
        'owner_city_state',
        'owner_postal_code',
        'building_home_energy_score_identifier',
        'generation_date',
        'release_date',
        'source_eui_weather_normalized',
        'site_eui_weather_normalized',
        'source_eui',
        'energy_alerts',
        'space_alerts',
        'building_certification',
        'lot_number',
        'city',
        'state',
        'postal_code',
        'number_properties',
        'block_number',
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
