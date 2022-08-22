/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_view', [])
  .controller('data_view_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      cycles
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.id = $stateParams.id;
      $scope.editing = false;

      let _collect_array_as_object = function (array) {
        ret = {};
        for (let i in array) {
          ret[array[i]['id']] = array[i];
        }
        return ret;
      };

      // load aggregations
      // todo: load in controller  
      $scope.aggregations = [
        {id: 1, name: 'Average'},
        {id: 2, name: 'Minimum'},
        {id: 3, name: 'Maximum'},
        {id: 4, name: 'Sum'},
        {id: 5, name: 'Count'}
      ];

      // load data views
      // todo: load in controller
      $scope.data_views = [
         {id: 1, name: 'Data View #1', filter_groups: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], cycles: [427, 428, 429], first_axis_source_column: 1, first_axis_aggregations: [1]},
         {id: 2, name: 'Data View #2', filter_groups: [1, 2], cycles: [427], first_axis_source_column: 2, first_axis_aggregations: [2]},
         {id: 3, name: 'Data View #3', filter_groups: [2, 4], cycles: [428], first_axis_source_column: 3, first_axis_aggregations: [3]},
         {id: 4, name: 'Data View #4', filter_groups: [1, 2, 3, 4], cycles: [427, 428], first_axis_source_column: 4, first_axis_aggregations: [4]},
         {id: 5, name: 'Data View #5', filter_groups: [1], cycles: [427], first_axis_source_column: 1, first_axis_aggregations: [1]},
         {id: 6, name: 'Data View #6', filter_groups: [1, 2], cycles: [427], first_axis_source_column: 2, first_axis_aggregations: [2]},
         {id: 7, name: 'Data View #7', filter_groups: [2, 4], cycles: [428], first_axis_source_column: 3, first_axis_aggregations: [3]},
         {id: 8, name: 'Data View #8', filter_groups: [1, 2, 3, 4], cycles: [427, 428], first_axis_source_column: 4, first_axis_aggregations: [4]},
         {id: 9, name: 'Data View #9', filter_groups: [1], cycles: [427], first_axis_source_column: 1, first_axis_aggregations: [1]},
         {id: 10, name: 'Data View #10', filter_groups: [1, 2], cycles: [427], first_axis_source_column: 2, first_axis_aggregations: [2]},
         {id: 11, name: 'Data View #11', filter_groups: [2, 4], cycles: [428], first_axis_source_column: 3, first_axis_aggregations: [3]},
         {id: 12, name: 'Data View #12', filter_groups: [1, 2, 3, 4], cycles: [427, 428], first_axis_source_column: 4, first_axis_aggregations: [4]}
      ];
      $scope.selected_data_view = $scope.id ? $scope.data_views.find(item => item.id === $scope.id) : null;

      // load cycles
      // todo: load selected_cycles from memory
      $scope.cycles = cycles.cycles;
      $scope.used_cycles = {};
      if ($scope.selected_data_view) {
        $scope.used_cycles = _collect_array_as_object($scope.cycles.filter(item => $scope.selected_data_view.cycles.includes(item.id)));
      }
      $scope.selected_cycles = Object.assign({}, $scope.used_cycles);
      $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;

      // load filter groups
      // todo: load in controller
      // todo: load selected_filter_groups from memory
      $scope.filter_groups = [
        {id: 1, name: 'Filter Group #1'},
        {id: 2, name: 'Filter Group #2'},
        {id: 3, name: 'Filter Group #3'},
        {id: 4, name: 'Filter Group #4'},
        {id: 5, name: 'Filter Group #5'},
        {id: 6, name: 'Filter Group #6'},
        {id: 7, name: 'Filter Group #7'},
        {id: 8, name: 'Filter Group #8'},
        {id: 9, name: 'Filter Group #9'},
        {id: 10, name: 'Filter Group #10'},
        {id: 11, name: 'Filter Group #11'},
        {id: 12, name: 'Filter Group #12'},
        {id: 13, name: 'Filter Group #13'},
        {id: 14, name: 'Filter Group #14'},
        {id: 15, name: 'Filter Group #15'},
        {id: 16, name: 'Filter Group #16'}
      ];
      $scope.used_filter_groups = {};
      if ($scope.selected_data_view) {
        $scope.used_filter_groups = _collect_array_as_object($scope.filter_groups.filter(item => $scope.selected_data_view.filter_groups.includes(item.id)));
      }
      $scope.selected_filter_groups = Object.assign({}, $scope.used_filter_groups);

      // load source columns
      // todo: load based on filter groups returned properties
      // todo: load source_column_by_location from memory
      $scope.source_columns = [
        {id: 1, name: 'Source Column #1', units: 'lbs'},
        {id: 2, name: 'Source Column #2', units: 'lbs'},
        {id: 3, name: 'Source Column #3', units: 'kg'},
        {id: 4, name: 'Source Column #4', units: 'kg'}
      ];
      $scope.source_column_by_location = {
        'first_axis': Object.assign({}, $scope.source_columns[0]),
        'second_axis': null
      };
      $scope.selected_table_location = 'first_axis';
      $scope.selected_table_aggregation = 1;

      $scope.object_has_key = function (a, b) {
        return Object.keys(a).includes(String(b));
      };
      $scope.object_has_any_key = function (a) {
        return Object.keys(a).length > 0;
      };

      $scope.toggle_filter_group = function (filter_group_id) {
        if (filter_group_id in $scope.selected_filter_groups) {
          delete $scope.selected_filter_groups[filter_group_id];
        } else {
          $scope.selected_filter_groups[filter_group_id] = Object.assign({}, $scope.used_filter_groups[filter_group_id]);
        }
      };

      $scope.toggle_cycle = function (cycle_id) {
        if (cycle_id in $scope.selected_cycles) {
          delete $scope.selected_cycles[cycle_id];
        } else {
          $scope.selected_cycles[cycle_id] = Object.assign({}, $scope.used_cycles[cycle_id]);
        }
        $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;
      };

      $scope.toggle_aggregation = function (location, aggregation_id) {
        if (!$scope.source_column_by_location[location]) {
          return;
        }
        let aggregations = null;
        switch (location) {
          case 'first_axis':
            aggregations = $scope.selected_data_view.first_axis_aggregations;
            break;
          case 'second_axis':
            aggregations = $scope.selected_data_view.second_axis_aggregations;
            break;
         default:
           return;
        }
        const i = aggregations.indexOf(aggregation_id);
        if (i > -1) {
          aggregations.splice(i, 1);
        } else {
          aggregations.push(aggregation_id);
        }
      };

      $scope.select_source_column = function (location, source_column_id) {
        if (source_column_id) {
          $scope.source_column_by_location[location] = Object.assign({}, $scope.source_columns.find(item => item.id == source_column_id));
        } else {
          $scope.source_column_by_location[location] = null;
        }
        switch (location) {
          case 'first_axis':
            $scope.selected_data_view.first_axis_aggregations = [];
            break;
          case 'second_axis':
            $scope.selected_data_view.second_axis_aggregations = [];
            break;
         default:

           return;
        }
      };
    }
  ]);
