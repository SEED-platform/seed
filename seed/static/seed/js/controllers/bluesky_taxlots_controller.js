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
  function(
    $scope,
    $routeParams,
    bluesky_service,
    taxlots
  ) {
      $scope.object = 'taxlot';

      $scope.columns = [
          'jurisdiction_taxlot_identifier',
          'block_number',
          'district',
          'address',
          // Property columns:
          'energy_score',
          'site_eui',
          'property_name'
      ];
      $scope.objects = taxlots.results;
      $scope.pagination = taxlots.pagination;

      $scope.number_per_page_options = [10, 25, 50];
      $scope.number_per_page = $scope.number_per_page_options[0];
      $scope.update_number_per_page = function(number) {
        $scope.number_per_page = number;
        bluesky_service.get_taxlots(1, number).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };
      $scope.pagination_first = function() {
        bluesky_service.get_taxlots(1, $scope.number_per_page).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };
      $scope.pagination_previous = function() {
        bluesky_service.get_taxlots($scope.pagination.page - 1, $scope.number_per_page).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };
      $scope.pagination_next = function() {
        bluesky_service.get_taxlots($scope.pagination.page + 1, $scope.number_per_page).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };
      $scope.pagination_last = function() {
        bluesky_service.get_taxlots($scope.pagination.num_pages, $scope.number_per_page).then(function(taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };
}]);
