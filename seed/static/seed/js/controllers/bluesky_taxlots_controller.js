/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.bluesky_taxlots_controller', [])
  .controller('bluesky_taxlots_controller', [
    '$scope',
    '$routeParams',
    '$window',
    'bluesky_service',
    'taxlots',
    'cycles',
    'columns',
    function ($scope,
              $routeParams,
              $window,
              bluesky_service,
              taxlots,
              cycles,
              columns) {
      $scope.object = 'taxlot';
      $scope.objects = taxlots.results;
      $scope.pagination = taxlots.pagination;
      $scope.number_per_page = 999999999;

      $scope.cycle = {
        selected_cycle: cycles[0],
        cycles: cycles
      };

      var refresh_objects = function () {
        bluesky_service.get_taxlots($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (taxlots) {
          $scope.objects = taxlots.results;
          $scope.pagination = taxlots.pagination;
        });
      };

      $scope.update_cycle = function (cycle) {
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      var defaults = {
        minWidth: 150
        //type: 'string'
      };
      _.map(columns, function (col) {
        var filter;
        if (col.type == 'number') filter = {filter: bluesky_service.numFilter()};
        else filter = {filter: bluesky_service.textFilter()};
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
            city: 'property_city',
            state: 'property_state',
            postal_code: 'property_postal_code'
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
        columnDefs: columns,
        treeCustomAggregations: bluesky_service.aggregations(),
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          $scope.updateHeight();
          angular.element($window).on('resize', _.debounce($scope.updateHeight, 150));
        }
      }
    }]);
