/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_properties_controller', [])
  .controller('bluesky_properties_controller', [
    '$scope',
    '$routeParams',
    '$window',
    'uiGridConstants',
    'bluesky_service',
    'properties',
    'cycles',
    'columns',
    'uiGridGroupingConstants',
    function ($scope,
              $routeParams,
              $window,
              uiGridConstants,
              bluesky_service,
              properties,
              cycles,
              cols,
              uiGridGroupingConstants) {
      $scope.object = 'property';
      $scope.objects = properties.results;
      $scope.pagination = properties.pagination;
      $scope.number_per_page = 999999999;

      $scope.cycle = {
        selected_cycle: cycles[0],
        cycles: cycles
      };

      var refresh_objects = function () {
        bluesky_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
        });
      };

      $scope.update_cycle = function (cycle) {
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      var textRegex = /^(!?)"(([^"]|\\")*)"$/;
      var textFilter = function () {
        return {
          condition: function (searchTerm, cellValue) {
            if (_.isNil(cellValue)) cellValue = '';
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
                var operator, value;
                if (!_.isUndefined(filterData[2])) {
                  // Equality condition
                  operator = filterData[1];
                  value = filterData[2];
                  if (_.isUndefined(operator) || _.startsWith(operator, '=')) {
                    // Equal
                    match = (value == 'null') ? (_.isNil(cellValue)) : (cellValue == value);
                    return match;
                  } else {
                    // Not equal
                    match = (value == 'null') ? (!_.isNil(cellValue)) : (cellValue != value);
                    return match;
                  }
                } else {
                  // Range condition
                  if (_.isNil(cellValue)) {
                    match = false;
                    return match;
                  }

                  operator = filterData[3];
                  value = Number(filterData[4]);
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

      var defaults = {
        minWidth: 150
        //type: 'string'
      };
      _.map(cols, function (col) {
        var filter;
        if (col.type == 'number') filter = {filter: numFilter()};
        else filter = {filter: textFilter()};
        return _.defaults(col, filter, defaults);
      });

      var data = angular.copy($scope.objects);
      var roots = data.length;
      for (var i = 0, trueIndex = 0; i < roots; ++i) {
        data[trueIndex].$$treeLevel = 0;
        var related = data[trueIndex].related;
        var relatedIndex = trueIndex;
        for (var j = 0; j < related.length; ++j) {
          // Rename nested keys
          var map = {
            city: 'tax_city',
            state: 'tax_state',
            postal_code: 'tax_postal_code'
          };
          var updated = _.reduce(related[j], function (result, value, key) {
            key = map[key] || key;
            result[key] = value;
            return result;
          }, {});

          data.splice(++trueIndex, 0, updated);
        }
        // Remove unnecessary data
        delete data[relatedIndex].collapsed;
        delete data[relatedIndex].related;
        ++trueIndex;
      }

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.buildingListControls', 'ul.nav'], function (selector) {
          height += angular.element(selector)[0].offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
      };

      $scope.gridOptions = {
        data: data,
        enableColumnMenus: false,
        enableFiltering: true,
        enableSorting: true,
        fastWatch: true,
        flatEntityAccess: true,
        showTreeExpandNoChildren: false,
        columnDefs: cols,
        treeCustomAggregations: {
          sum: {
            aggregationFn: function (aggregation, fieldValue) {
              if (!_.has(aggregation, 'values')) aggregation.values = [fieldValue];
              else aggregation.values.push(fieldValue);
            },
            finalizerFn: function (aggregation) {
              var sum = _.sum(aggregation.values);
              aggregation.value = sum ? sum : null;
            }
          },
          uniqueList: {
            aggregationFn: function (aggregation, fieldValue) {
              if (!_.has(aggregation, 'values')) aggregation.values = [fieldValue];
              else aggregation.values.push(fieldValue);
            },
            finalizerFn: function (aggregation) {
              aggregation.value = _.join(_.uniq(aggregation.values), '; ');
            }
          }
        },
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          $scope.updateHeight();
          angular.element($window).on('resize', _.debounce($scope.updateHeight, 150));
        }
      }
    }]);
