/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_properties_controller', [])
  .controller('bluesky_properties_controller', [
    '$scope',
    '$routeParams',
    'uiGridConstants',
    'bluesky_service',
    'properties',
    'cycles',
    'columns',
    'uiGridGroupingConstants',
    function ($scope,
              $routeParams,
              uiGridConstants,
              bluesky_service,
              properties,
              cycles,
              columns,
              uiGridGroupingConstants) {
      $scope.object = 'property';
      $scope.objects = properties.results;

      $scope.columns = columns;

      var refresh_objects = function () {
        bluesky_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
        });
      };

      $scope.expanded = true;
      $scope.toggleExpanded = function () {
        $scope.expanded = !$scope.expanded;
      };

      /*$scope.gridExpanded = false;
       $scope.expandAll = function () {
       $scope.gridExpanded = !$scope.gridExpanded;
       };*/

      $scope.cycle = {
        selected_cycle: cycles[0],
        cycles: cycles
      };
      $scope.update_cycle = function (cycle) {
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      $scope.pagination = properties.pagination;
      $scope.number_per_page_options = [10, 25, 50];
      $scope.number_per_page = 999999999;
      $scope.update_number_per_page = function (number) {
        $scope.number_per_page = number;
        $scope.pagination.page = 1;
        refresh_objects();
      };
      $scope.pagination_first = function () {
        $scope.pagination.page = 1;
        refresh_objects();
      };
      $scope.pagination_previous = function () {
        $scope.pagination.page--;
        refresh_objects();
      };
      $scope.pagination_next = function () {
        $scope.pagination.page++;
        refresh_objects();
      };
      $scope.pagination_last = function () {
        $scope.pagination.page = $scope.pagination.num_pages;
        refresh_objects();
      };

      var textRegex = /^(!?)"(([^"]|\\")*)"$/;
      var textFilter = function () {
        return {
          condition: function (searchTerm, cellValue) {
            var filterData = searchTerm.match(textRegex);
            var regex;
            if (filterData) {
              var inverse = filterData[1] == '!';
              var value = filterData[2];
              regex = new RegExp('^' + _.escapeRegExp(value) + '$');
              return inverse ? !regex.test(cellValue) : regex.test(cellValue);
            } else {
              regex = new RegExp(_.escapeRegExp(searchTerm), 'i');
              return regex.test(cellValue);
            }
          }
        };
      };

      var numRegex = /^(==?|!=?|<>)?\s*(null|-?\d+)|(<=?|>=?)\s*(-?\d+)$/;
      var numFilter = function () {
        return {
          condition: function (searchTerm, cellValue) {
            var match = true;
            var searchTerms = _.map(_.split(searchTerm, ','), _.trim);
            _.forEach(searchTerms, function (search) {
              var filterData = search.match(numRegex);
              if (filterData) {
                if (!_.isUndefined(filterData[2])) {
                  // Equality condition
                  var operator = filterData[1];
                  var value = filterData[2];
                  if (_.isUndefined(operator) || _.startsWith(operator, '=')) {
                    // Equal
                    match = (value == 'null') ? (_.isNull(cellValue)) : (cellValue == value);
                    return match;
                  } else {
                    // Not equal
                    match = (value == 'null') ? (!_.isNull(cellValue)) : (cellValue != value);
                    return match;
                  }
                } else {
                  // Range condition
                  if (_.isNull(cellValue)) {
                    match = false;
                    return match;
                  }

                  var operator = filterData[3];
                  var value = Number(filterData[4]);
                  switch (operator) {
                    case '<':
                      match = cellValue < value;
                      return match;
                    case '<=':
                      match = cellValue <= value;
                      return match;
                    case '>':
                      match = cellValue > value;
                      return match;
                    case '>=':
                      match = cellValue >= value;
                      return match;
                  }
                }
              } else {
                match = false;
                return match;
              }
            });
            return match;
          }
        };
      };

      var cols = [
        {name: 'building_portfolio_manager_identifier', displayName: 'PM Property ID', type: 'number'},
        {name: 'jurisdiction_property_identifier', displayName: 'Property/Building ID', type: 'number'},
        {name: 'jurisdiction_taxlot_identifier', displayName: 'Tax Lot ID', type: 'number', treeAggregationType: 'list', customTreeAggregationFinalizerFn: function( aggregation ) {
        aggregation.rendered = aggregation.value;}},
        {name: 'primary', displayName: 'Primary/Secondary'},
        {name: 'associated_tax_lot_ids'},
        {name: 'lot_number', displayName: 'Associated Building Tax Lot ID', type: 'number'},
        {name: 'address', displayName: 'Tax Lot Address', treeAggregationType: 'list', customTreeAggregationFinalizerFn: function( aggregation ) {
        aggregation.rendered = aggregation.value;}},
        {name: 'address_line_1', displayName: 'Property Address 1', type: 'numberStr'},
        {name: 'city', displayName: 'Property City'},
        {name: 'property_name'},
        {name: 'campus'},
        {name: 'pm_parent_property_id', type: 'number'},
        {name: 'gross_floor_area', displayName: 'Property Floor Area', type: 'number'},
        {name: 'use_description', displayName: 'Property Type'},
        {name: 'energy_score', displayName: 'ENERGY STAR Score', type: 'number'},
        {name: 'site_eui', displayName: 'Site EUI (kBtu/sf-yr)', type: 'number'},
        {name: 'property_notes'},
        {name: 'year_ending', displayName: 'Benchmarking year'},
        {name: 'owner'},
        {name: 'owner_email'},
        {name: 'owner_telephone'},
        {name: 'pm_generation_date', displayName: 'PM Generation Date'},
        {name: 'pm_release_date', displayName: 'PM Release Date'},
        {name: 'address_line_2', displayName: 'Property Address 2'},
        {name: 'state', displayName: 'Property State'},
        {name: 'postal_code', displayName: 'Property Postal Code'},
        {name: 'building_count', displayName: 'Number of Buildings', type: 'number'},
        {name: 'year_built', type: 'number'},
        {name: 'recent_sale_date', displayName: 'Property Sale Date'},
        {name: 'conditioned_floor_area', displayName: 'Property Conditioned Floor Area', type: 'number'},
        {name: 'occupied_floor_area', displayName: 'Property Occupied Floor Area', type: 'number'},
        {name: 'owner_address'},
        {name: 'owner_city_state', displayName: 'Owner City/State'},
        {name: 'owner_postal_code'},
        {name: 'building_home_energy_score_identifier', displayName: 'Home Energy Saver ID'},
        {name: 'generation_date', displayName: 'Generation Date'},
        {name: 'release_date', displayName: 'Release Date'},
        {name: 'source_eui_weather_normalized'},
        {name: 'site_eui_weather_normalized'},
        {name: 'source_eui'},
        {name: 'energy_alerts'},
        {name: 'space_alerts'},
        {name: 'building_certification'},
        {name: 'tax_city', displayName: 'Tax Lot City'},
        {name: 'tax_state', displayName: 'Tax Lot State'},
        {name: 'tax_postal_code', displayName: 'Tax Lot Postal Code'},
        {name: 'number_properties'},
        {name: 'block_number'},
        {name: 'district'}
      ];

      var defaults = {
        minWidth: 150
        //type: 'string'
      };
      //var exclude = ['extra_data'];
      /*var cols = _.map(_.difference(_.keys($scope.objects[0]), exclude).sort(), function (key) {
       return _.defaults({name: key}, defaults);
       });*/
      _.map(cols, function (col) {
        var filter;
        if (col.type == 'number') filter = {filter: numFilter()};
        else filter = {filter: textFilter()};
        return _.defaults(col, filter, defaults);
      });
      //console.debug(cols);

      //console.debug($scope.objects);

      var data = angular.copy($scope.objects);
      var roots = data.length;
      for (var i = 0, trueIndex = 0; i < roots; i++) {
        data[trueIndex].$$treeLevel = 0;
        var related = data[trueIndex].related;
        for (var j = 0; j < related.length; j++) {
          related[j].tax_city = related[j].city;
          data.splice(++trueIndex, 0, related[j]);
        }
        trueIndex++;
      }

      $scope.gridOptions = {
        data: data,
        enableColumnMenus: false,
        enableFiltering: true,
        enableSorting: true,
        fastWatch: true,
        flatEntityAccess: true,
        minRowsToShow: 26,
        paginationPageSizes: [10, 25, 50],
        paginationPageSize: 25,
        showTreeExpandNoChildren: false,
        columnDefs: cols,
        treeCustomAggregations: {
          list: {
            label: 'list',
            aggregationFn: function (aggregation, fieldValue, numValue) {
              //console.debug('aggregationFn', aggregation, fieldValue, numValue);
              if (!_.has(aggregation, 'value')) aggregation.value = fieldValue;
              else aggregation.value += '; ' + fieldValue;
              //aggregation.count = (aggregation.count || 1) + 1;
              //aggregation.sum = (aggregation.sum || 0) + numValue;
            },
            finalizerFn: function (aggregation) {
              //aggregation.value = 'hi'
            }
          }
        },
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
        }
      }
    }]);
