/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.properties_controller', [])
  .controller('properties_controller', [
    '$scope',
    '$window',
    'property_taxlot_service',
    'properties',
    'cycles',
    'columns',
    function ($scope,
              $window,
              property_taxlot_service,
              properties,
              cycles,
              columns) {
      $scope.object = 'property';
      $scope.objects = properties.results;
      $scope.pagination = properties.pagination;
      $scope.number_per_page = 999999999;
      $scope.restoring = false;

      var lastCycleId = property_taxlot_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: lastCycleId ? _.find(cycles, {pk: lastCycleId}) : cycles[0],
        cycles: cycles
      };

      var processData = function () {
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
        $scope.data = data;
      };

      var refresh_objects = function () {
        property_taxlot_service.get_properties($scope.pagination.page, $scope.number_per_page, $scope.cycle.selected_cycle).then(function (properties) {
          $scope.objects = properties.results;
          $scope.pagination = properties.pagination;
          processData();
        });
      };

      $scope.update_cycle = function (cycle) {
        property_taxlot_service.save_last_cycle(cycle.pk);
        $scope.cycle.selected_cycle = cycle;
        refresh_objects();
      };

      processData();

      var defaults = {
        minWidth: 75,
        width: 150
        //type: 'string'
      };
      _.map(columns, function (col) {
        var filter = aggregation = {};
        if (col.type == 'number') filter = {filter: property_taxlot_service.numFilter()};
        else filter = {filter: property_taxlot_service.textFilter()};
        if (col.related) aggregation.treeAggregationType = 'uniqueList';
        return _.defaults(col, filter, aggregation, defaults);
      });

      var updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.buildingListControls', 'ul.nav'], function (selector) {
          height += angular.element(selector)[0].offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
      };

      var saveState = function () {
        if (!$scope.restoring) {
          localStorage.setItem('grid.properties', JSON.stringify($scope.gridApi.saveState.save()));
        }
      };

      var restoreState = function () {
        $scope.restoring = true;
        var state = localStorage.getItem('grid.properties');
        if (!_.isNull(state)) {
          state = JSON.parse(state);
          $scope.gridApi.saveState.restore($scope, state);
        }
        _.defer(function () {
          $scope.restoring = false;
        });
      };

      var restoreDefaultState = function () {
        $scope.gridApi.saveState.restore($scope, $scope.defaultState);
      };

      $scope.gridOptions = {
        data: 'data',
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: true,
        exporterCsvFilename: 'Property Data.csv',
        exporterMenuPdf: false,
        fastWatch: true,
        flatEntityAccess: true,
        gridMenuCustomItems: [{
          title: 'Reset settings',
          action: restoreDefaultState
        }],
        saveFocus: false,
        saveGrouping: false,
        saveGroupingExpandedStates: false,
        saveScroll: false,
        saveSelection: false,
        saveTreeView: false,
        showTreeExpandNoChildren: false,
        columnDefs: columns,
        treeCustomAggregations: property_taxlot_service.aggregations(),
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          updateHeight();
          angular.element($window).on('resize', _.debounce(updateHeight, 150));

          gridApi.colMovable.on.columnPositionChanged($scope, saveState);
          gridApi.colResizable.on.columnSizeChanged($scope, saveState);
          gridApi.core.on.columnVisibilityChanged($scope, saveState);
          gridApi.core.on.filterChanged($scope, saveState);
          gridApi.core.on.sortChanged($scope, saveState);
          gridApi.pinning.on.columnPinned($scope, saveState);

          _.defer(function () {
            $scope.defaultState = $scope.gridApi.saveState.save();
            restoreState();
          });
        }
      }
    }]);
