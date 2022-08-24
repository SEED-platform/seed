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
    'data_views',
    'data_view_service',
    'property_columns',
    'taxlot_columns',
    'valid_column_data_types',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      cycles,
      data_views,
      data_view_service,
      property_columns,
      taxlot_columns,
      valid_column_data_types
    ) {
      $scope.id = $stateParams.id;
      $scope.valid_column_data_types = valid_column_data_types;
      $scope.editing = false;
      $scope.create_errors = [];
      $scope.data_views_error = null;
      $scope.fields = {
        'filter_group_checkboxes': {},
        'cycle_checkboxes': {},
        'name': ''
      };

      let _init_fields = function () {
        for (let i in $scope.filter_groups) {
          $scope.fields.filter_group_checkboxes[$scope.filter_groups[i].id] = false;
        }
        for (let i in $scope.cycles) {
          $scope.fields.cycle_checkboxes[$scope.cycles[i].id] = false;
        }
        $scope.source_column_by_location['first_axis'] = null;
        $scope.source_column_by_location['second_axis'] = null;
      };

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
      $scope.data_views = data_views;
      if (data_views.status == 'error') {
        $scope.data_views_error = data_views.message;
      }
      $scope.has_data_views = $scope.data_views.length > 0;
      console.log($scope.data_views);
      $scope.selected_data_view = $scope.id ? Object.assign({}, $scope.data_views.find(item => item.id === $scope.id)) : null;
      console.log($scope.selected_data_view);

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
      $scope.source_columns = {
        'property': property_columns,
        'taxlot': taxlot_columns,
        'by_id': Object.assign(_collect_array_as_object(property_columns), _collect_array_as_object(taxlot_columns))
      };
      $scope.source_column_by_location = {
        'first_axis': Object.assign({}, $scope.source_columns['property'][0]),
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
          $scope.source_column_by_location[location] = Object.assign({}, $scope.source_columns.by_id[source_column_id]);
        } else {
          $scope.source_column_by_location[location] = null;
        }
        if ($scope.editing) {
          return;
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

      $scope.click_new_data_view = function() {
        $scope.selected_data_view = {
          name: 'New Data View',
          first_axis_aggregations: [],
          second_axis_aggregations: []
        };
        $scope.editing = true;
      };

      $scope.click_save_changes = function() {
        $scope.create_errors = [];

        // validate name
        if (!$scope.fields.name) {
          $scope.create_errors.push("A name is required.");
        }

        // validate filter groups
        let checked_filter_groups = [];
        for (let i in $scope.fields.filter_group_checkboxes) {
          if ($scope.fields.filter_group_checkboxes[i]) {
            checked_filter_groups.push(parseInt(i));
          }
        }
        if (checked_filter_groups.length < 1) {
         $scope.create_errors.push("At least one filter group must be selected.");
        }

        // validate cycles
        let checked_cycles = [];
        for (let i in $scope.fields.cycle_checkboxes) {
          if ($scope.fields.cycle_checkboxes[i]) {
            checked_cycles.push(parseInt(i));
          }
        }
        if (checked_cycles.length < 1) {
         $scope.create_errors.push("At least one cycle must be selected.");
        }

        // validate column
        if (!$scope.source_column_by_location['first_axis']) {
          $scope.create_errors.push("The first axis must have a source column.");
        }
        if ($scope.selected_data_view.first_axis_aggregations.length < 1) {
          $scope.create_errors.push("The first axis needs at least one selected aggregation.");
        }
        if ($scope.source_column_by_location['second_axis'] && $scope.selected_data_view.second_axis_aggregations.length < 1) {
          $scope.create_errors.push("The second axis needs at least one selected aggregation.");
        }

        // any errors?
        if ($scope.create_errors.length > 0) {
          return;
        }

        // create data view
        let filter_groups = {'name': 'fg_name', 'query_dict': {'site_eui__gt': 1}};
        let aggregations = [];
        if ($scope.source_column_by_location['first_axis']) {
          aggregations.push({
            "column": $scope.source_column_by_location['first_axis']['id'],
            "location": 'first_axis',
            "aggregations": $scope.selected_data_view.first_axis_aggregations
          });
        }
        if ($scope.source_column_by_location['second_axis']) {
          aggregations.push({
            "column": $scope.source_column_by_location['second_axis'][id],
            "location": 'second_axis',
            "aggregations": $scope.selected_data_view.second_axis_aggregations
          });
        }
        let new_data_view = data_view_service.create_data_view($scope.fields.name, filter_groups, checked_cycles, aggregations);
        console.log(new_data_view);

        // done
        _init_fields();
        $scope.editing = false;
      };

      _init_fields();

      $scope.click_cancel = function() {
        $scope.selected_data_view = null;
        $scope.create_errors = [];
        _init_fields();
        $scope.editing = false;
      };
    }
  ]);
