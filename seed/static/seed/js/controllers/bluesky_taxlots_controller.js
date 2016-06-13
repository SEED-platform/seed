/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_taxlots_controller', [])
.controller('bluesky_taxlots_controller', [
  '$scope',
  '$routeParams',
  'bluesky_service',
  'taxlots',
  'cycles',
  function(
    $scope,
    $routeParams,
    bluesky_service,
    taxlots,
    cycles
  ) {
      $scope.object = 'taxlot';

      $scope.columns = [
        {field: 'jurisdiction_taxlot_identifier', display: 'Tax Lot ID', related: false},
        {field: 'no_field', display: 'Associated TaxLot IDs', related: false},
        {field: 'no_field', display: 'Associated Building Tax Lot ID', related: false},
        {field: 'address', display: 'Tax Lot Address', related: false},
        {field: 'city', display: 'Tax Lot City', related: false},
        {field: 'state', display: 'Tax Lot State', related: false},
        {field: 'postal_code', display: 'Tax Lot Postal Code', related: false},
        {field: 'number_properties', display: 'Number Properties', related: false},
        {field: 'block_number', display: 'Block Number', related: false},
        {field: 'district', display: 'District', related: false},
        {field: 'primary', display: 'Primary/Secondary', related: true},
        {field: 'property_name', display: 'Property Name', related: true},
        {field: 'campus', display: 'Campus', related: true},
        {field: 'no_field', display: 'PM Parent Property ID', related: false},
        {field: 'jurisdiction_property_identifier', display: 'Property / Building ID', related: true},
        {field: 'building_portfolio_manager_identifier', display: 'PM Property ID', related: true},
        {field: 'gross_floor_area', display: 'Property Floor Area', related: true},
        {field: 'use_description', display: 'Property Type', related: true},
        {field: 'energy_score', display: 'ENERGY STAR Score', related: true},
        {field: 'site_eui', display: 'Site EUI (kBtu/sf-yr)', related: true},
        {field: 'property_notes', display: 'Property Notes', related: true},
        {field: 'year_ending', display: 'Benchmarking year', related: true},
        {field: 'owner', display: 'Owner', related: true},
        {field: 'owner_email', display: 'Owner Email', related: true},
        {field: 'owner_telephone', display: 'Owner Telephone', related: true},
        {field: 'generation_date', display: 'PM Generation Date', related: true},
        {field: 'release_date', display: 'PM Release Date', related: true},
        {field: 'address_line_1', display: 'Property Address 1', related: true},
        {field: 'address_line_2', display: 'Property Address 2', related: true},
        {field: 'city', display: 'Property City', related: true},
        {field: 'state', display: 'Property State', related: true},
        {field: 'postal_code', display: 'Property Postal Code', related: true},
        {field: 'building_count', display: 'Number of Buildings', related: true},
        {field: 'year_built', display: 'Year Built', related: true},
        {field: 'recent_sale_date', display: 'Property Sale Data', related: true},
        {field: 'conditioned_floor_area', display: 'Property Conditioned Floor Area', related: true},
        {field: 'occupied_floor_area', display: 'Property Occupied Floor Area', related: true},
        {field: 'owner_address', display: 'Owner Address', related: true},
        {field: 'owner_city_state', display: 'Owner City/State', related: true},
        {field: 'owner_postal_code', display: 'Owner Postal Code', related: true},
        {field: 'building_home_energy_score_identifier', display: 'Home Energy Saver ID', related: true},
        {field: 'source_eui_weather_normalized', display: 'Source EUI Weather Normalized', related: true},
        {field: 'site_eui_weather_normalized', display: 'Site EUI Normalized', related: true},
        {field: 'source_eui', display: 'Source EUI', related: true},
        {field: 'energy_alerts', display: 'Energy Alerts', related: true},
        {field: 'space_alerts', display: 'Space Alerts', related: true},
        {field: 'building_certification', display: 'Building Certification', related: true},
        {field: 'lot_number', display: 'Associated Tax Lot ID', related: true}
      ];
      $scope.objects = taxlots.results;

      var refresh_objects = function() {
        bluesky_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
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

      $scope.pagination = taxlots.pagination;
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
