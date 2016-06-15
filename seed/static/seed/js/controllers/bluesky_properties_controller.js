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
        {field: 'building_portfolio_manager_identifier', display: 'PM Property ID', related: false},
        {field: 'jurisdiction_property_identifier', display: 'Property / Building ID', related: false},
        {field: 'jurisdiction_taxlot_identifier', display: 'Tax Lot ID', related: true},
        {field: 'primary', display: 'Primary/Secondary', related: true},
        {field: 'no_field', display: 'Associated TaxLot IDs', related: false},
        {field: 'no_field', display: 'Associated Building Tax Lot ID', related: false},
        {field: 'address', display: 'Tax Lot Address', related: true},
        {field: 'address_line_1', display: 'Property Address 1', related: false},
        {field: 'city', display: 'Property City', related: false},
        {field: 'property_name', display: 'Property Name', related: false},
        {field: 'campus', display: 'Campus', related: false},
        {field: 'no_field', display: 'PM Parent Property ID', related: false},
        {field: 'gross_floor_area', display: 'Property Floor Area', related: false},
        {field: 'use_description', display: 'Property Type', related: false},
        {field: 'energy_score', display: 'ENERGY STAR Score', related: false},
        {field: 'site_eui', display: 'Site EUI (kBtu/sf-yr)', related: false},
        {field: 'property_notes', display: 'Property Notes', related: false},
        {field: 'year_ending', display: 'Benchmarking year', related: false},
        {field: 'owner', display: 'Owner', related: false},
        {field: 'owner_email', display: 'Owner Email', related: false},
        {field: 'owner_telephone', display: 'Owner Telephone', related: false},
        {field: 'generation_date', display: 'PM Generation Date', related: false},
        {field: 'release_date', display: 'PM Release Date', related: false},
        {field: 'address_line_2', display: 'Property Address 2', related: false},
        {field: 'state', display: 'Property State', related: false},
        {field: 'postal_code', display: 'Property Postal Code', related: false},
        {field: 'building_count', display: 'Number of Buildings', related: false},
        {field: 'year_built', display: 'Year Built', related: false},
        {field: 'recent_sale_date', display: 'Property Sale Data', related: false},
        {field: 'conditioned_floor_area', display: 'Property Conditioned Floor Area', related: false},
        {field: 'occupied_floor_area', display: 'Property Occupied Floor Area', related: false},
        {field: 'owner_address', display: 'Owner Address', related: false},
        {field: 'owner_city_state', display: 'Owner City/State', related: false},
        {field: 'owner_postal_code', display: 'Owner Postal Code', related: false},
        {field: 'building_home_energy_score_identifier', display: 'Home Energy Saver ID', related: false},
        {field: 'source_eui_weather_normalized', display: 'Source EUI Weather Normalized', related: false},
        {field: 'site_eui_weather_normalized', display: 'Site EUI Normalized', related: false},
        {field: 'source_eui', display: 'Source EUI', related: false},
        {field: 'energy_alerts', display: 'Energy Alerts', related: false},
        {field: 'space_alerts', display: 'Space Alerts', related: false},
        {field: 'building_certification', display: 'Building Certification', related: false},
        {field: 'city', display: 'Tax Lot City', related: true},
        {field: 'state', display: 'Tax Lot State', related: true},
        {field: 'postal_code', display: 'Tax Lot Postal Code', related: true},
        {field: 'number_properties', display: 'Number Properties', related: true},
        {field: 'block_number', display: 'Block Number', related: true},
        {field: 'district', display: 'District', related: true}
      ];
      $scope.objects = properties.results;

      var refresh_objects = function() {
        bluesky_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function(properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
        });
      };

      $scope.expanded = true;
      $scope.toggleExpanded = function() {
          $scope.expanded = !$scope.expanded;
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
