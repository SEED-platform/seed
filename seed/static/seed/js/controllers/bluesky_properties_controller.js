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
        {field: 'building_portfolio_manager_identifier', display: 'PM Property ID'},
        {field: 'jurisdiction_property_identifier', display: 'Property / Building ID'},
        {field: 'jurisdiction_tax_lot_identifier', display: 'Tax Lot ID'},
        {field: 'primary', display: 'Primary/Secondary'},
        {field: 'no_field', display: 'Associated TaxLot IDs'},
        {field: 'no_field', display: 'Associated Building Tax Lot ID'},
        {field: 'address', display: 'Tax Lot Address'},
        {field: 'address_line_1', display: 'Property Address 1'},
        {field: 'city', display: 'Property City'},
        {field: 'property_name', display: 'Property Name'},
        {field: 'campus', display: 'Campus'},
        {field: 'no_field', display: 'PM Parent Property ID'},
        {field: 'gross_floor_area', display: 'Property Floor Area'},
        {field: 'use_description', display: 'Property Type'},
        {field: 'energy_score', display: 'ENERGY STAR Score'},
        {field: 'site_eui', display: 'Site EUI (kBtu/sf-yr)'},
        {field: 'property_notes', display: 'Property Notes'},
        {field: 'year_ending', display: 'Benchmarking year'},
        {field: 'owner', display: 'Owner'},
        {field: 'owner_email', display: 'Owner Email'},
        {field: 'owner_telephone', display: 'Owner Telephone'},
        {field: 'generation_date', display: 'PM Generation Date'},
        {field: 'release_date', display: 'PM Release Date'},
        {field: 'address_line_2', display: 'Property Address 2'},
        {field: 'state', display: 'Property State'},
        {field: 'postal_code', display: 'Property Postal Code'},
        {field: 'building_count', display: 'Number of Buildings'},
        {field: 'year_built', display: 'Year Built'},
        {field: 'recent_sale_date', display: 'Property Sale Data'},
        {field: 'conditioned_floor_area', display: 'Property Conditioned Floor Area'},
        {field: 'occupied_floor_area', display: 'Property Occupied Floor Area'},
        {field: 'owner_address', display: 'Owner Address'},
        {field: 'owner_city_state', display: 'Owner City/State'},
        {field: 'owner_postal_code', display: 'Owner Postal Code'},
        {field: 'building_home_energy_score_identifier', display: 'Home Energy Saver ID'},
        {field: 'generation_date', display: 'Generation Data'},
        {field: 'release_date', display: 'Release Data'},
        {field: 'source_eui_weather_normalized', display: 'Source EUI Weather Normalized'},
        {field: 'site_eui_weather_normalized', display: 'Site EUI Normalized'},
        {field: 'source_eui', display: 'Source EUI'},
        {field: 'energy_alerts', display: 'Energy Alerts'},
        {field: 'space_alerts', display: 'Space Alerts'},
        {field: 'building_certification', display: 'Building Certification'},
        {field: 'city', display: 'Tax Lot City'},
        {field: 'state', display: 'Tax Lot State'},
        {field: 'postal_code', display: 'Tax Lot Postal Code'},
        {field: 'number_properties', display: 'Number Properties'},
        {field: 'block_number', display: 'Block Number'},
        {field: 'district', display: 'District'}
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
