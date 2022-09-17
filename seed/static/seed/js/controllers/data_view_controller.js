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
    'filter_groups',
    'data_view_service',
    'property_columns',
    'spinner_utility',
    'taxlot_columns',
    'valid_column_data_types',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      cycles,
      data_views,
      filter_groups,
      data_view_service,
      property_columns,
      spinner_utility,
      taxlot_columns,
      valid_column_data_types
    ) {
      spinner_utility.show();
      $scope.id = $stateParams.id;
      $scope.valid_column_data_types = valid_column_data_types;
      $scope.editing = false;
      $scope.create_errors = [];
      $scope.data_views_error = null;
      $scope.cycles = cycles.cycles;
      $scope.fields = {
        'filter_group_checkboxes': {},
        'cycle_checkboxes': {},
        'name': ''
      };
      $scope.show_properties_for_filter_group = {};
      $scope.aggregations = [
        {id: 1, name: 'Average'},
        {id: 2, name: 'Minimum'},
        {id: 3, name: 'Maximum'},
        {id: 4, name: 'Sum'},
        {id: 5, name: 'Count'}
      ];
      $scope.filter_groups = filter_groups
      console.log('filter_groups',$scope.filter_groups)

      $scope.show_config = true
      $scope.toggle_config = () => {
        console.log('toggle config')
        $scope.show_config = !$scope.show_config
      }

      let _collect_array_as_object = function (array, key="id") {
        ret = {};
        for (let i in array) {
          ret[array[i][key]] = array[i];
        }
        return ret;
      };

      let _collect_array_as_object_sorted = function (array, key="start") {
        ret = {};
        for (let i in array) {
          ret[array[i][key]] = array[i];
        }
        return ret;
      };

      let _init_fields = function () {
        for (let i in $scope.filter_groups) {
          $scope.fields.filter_group_checkboxes[$scope.filter_groups[i].id] = false;
        }
        for (let i in $scope.cycles) {
          $scope.fields.cycle_checkboxes[$scope.cycles[i].id] = false;
        }
        $scope.source_column_by_location = {'first_axis': null, 'second_axis': null};
      };

      let _init_data = function () {

        // load data views
        $scope.data_views = data_views;
        if (data_views.status == 'error') {
          $scope.data_views_error = data_views.message;
        }
        $scope.has_data_views = $scope.data_views.length > 0;
        $scope.selected_data_view = $scope.id ? $scope.data_views.find(item => item.id === $scope.id) : null;
        if ($scope.selected_data_view) {
          $scope.selected_data_view.first_axis_aggregations = [];
          $scope.selected_data_view.second_axis_aggregations = [];
        } else if ($scope.id) {
          $scope.data_views_error = 'Could not find Data View with id #' + $scope.id + '!';
        }

        // load cycles
        $scope.used_cycles = {};
        if ($scope.selected_data_view) {
          $scope.used_cycles = _collect_array_as_object_sorted($scope.cycles.filter(item => $scope.selected_data_view.cycles.includes(item.id)));
        }
        $scope.selected_cycles = Object.assign({}, $scope.used_cycles);
        $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;

        // load source columns
        $scope.source_columns = {
          'property': property_columns,
          'taxlot': taxlot_columns,
          'by_id': Object.assign(_collect_array_as_object(property_columns), _collect_array_as_object(taxlot_columns))
        };

        // load both axis
        if ($scope.selected_data_view) {
          let first_axis_aggregations = $scope.selected_data_view.parameters.find(item => item.location == 'first_axis');
          if (first_axis_aggregations) {
            $scope.selected_table_location = 'first_axis';
            $scope.selected_table_aggregation = first_axis_aggregations['aggregations'][0];
            $scope.select_source_column('first_axis', first_axis_aggregations.column, false);
            for (let i in first_axis_aggregations['aggregations']) {
              $scope.toggle_aggregation('first_axis', first_axis_aggregations['aggregations'][i]);
            }
          }
          let second_axis_aggregations = $scope.selected_data_view.parameters.find(item => item.location == 'second_axis');
          if (second_axis_aggregations) {
            $scope.select_source_column('second_axis', second_axis_aggregations.column, false);
            for (let i in second_axis_aggregations['aggregations']) {
              $scope.toggle_aggregation('second_axis', second_axis_aggregations['aggregations'][i]);
            }
          }
        }

        // load filter groups
        $scope.used_filter_groups = {};
        if ($scope.selected_data_view) {
          $scope.used_filter_groups = $scope.filter_groups
          .filter(fg => $scope.selected_data_view.filter_groups.includes(fg.id))
          .reduce((acc, curr) => {
            acc[curr.name] = curr
            return acc
          }, {})
          for (let i in $scope.selected_data_view.filter_groups) {
            $scope.show_properties_for_filter_group[$scope.selected_data_view.filter_groups[i]] = false;
          }
        }
        $scope.selected_filter_groups = Object.assign({}, $scope.used_filter_groups);
      };

      $scope.data = {};
      let _load_data = function () {
        if (!$scope.selected_data_view) {
          spinner_utility.hide();
          return;
        }
        spinner_utility.show();
        let data = data_view_service.evaluate_data_view($scope.selected_data_view.id, Object.values($scope.source_column_by_location).filter(item => item).map(item => item.id)).then((data) => {
          $scope.data = data;
          spinner_utility.hide();
        }).then(() => {
          _build_chart();
        });
      };

      $scope.object_has_key = function (a, b) {
        return Object.keys(a).includes(String(b));
      };
      $scope.object_has_any_key = function (a) {
        return Object.keys(a).length > 0;
      };

      $scope.toggle_filter_group = function (filter_group_id) {
        filter_group = $scope.filter_groups.find(fg => fg.id == filter_group_id)
        if (filter_group.name in $scope.selected_filter_groups) {
          delete $scope.selected_filter_groups[filter_group.name];
        } else {
          $scope.selected_filter_groups[filter_group.name] = Object.assign({}, $scope.used_filter_groups[filter_group.name]);
        }
        console.log('_assign_datasets toggle filter group')
        _assign_datasets();
      };

      $scope.toggle_cycle = function (cycle_id) {
        if (cycle_id in $scope.selected_cycles) {
          delete $scope.selected_cycles[cycle_id];
        } else {
          $scope.selected_cycles[cycle_id] = Object.assign({}, $scope.used_cycles[cycle_id]);
        }
        $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;
        console.log('selected cycles', $scope.selected_cycles)
        console.log('used cycles', $scope.used_cycles)
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
        if ($scope.dataViewChart) {
          console.log('_assign_datasets toggle agg')
          _assign_datasets()
        }
      };

      $scope.select_source_column = function (location, source_column_id, reload_data=true) {
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
            console.log('set second axis [] 236')
            $scope.selected_data_view.second_axis_aggregations = [];
            break;
         default:
           return;
        }
        if (reload_data) {
          _load_data();
        }
        console.log('_assign_datasets select source column')
        _assign_datasets();
      };

      $scope.click_new_data_view = function () {
        spinner_utility.show();
        $scope.selected_data_view = {
          name: 'New Custom Report',
          first_axis_aggregations: [],
          second_axis_aggregations: []
        };
        $scope.editing = true;
        spinner_utility.hide();
      };

      $scope.click_save_changes = function () {
        spinner_utility.show();
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
          console.log('errors', $scope.create_errors)
          spinner_utility.hide();
          return;
        }

        // create/update data view
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
            "column": $scope.source_column_by_location['second_axis']['id'],
            "location": 'second_axis',
            "aggregations": $scope.selected_data_view.second_axis_aggregations
          });
        }

        let _done = function (data) {
            if (data.status == 'success') {
              if (!$scope.selected_data_view.id) {
                window.location = '#/insights/custom/' + data.data_view.id;
                spinner_utility.hide();
                return;
              }
              data_views = data_views.map(data_view => {
                if (data_view.id == data.data_view.id) {
                  return Object.assign({}, data.data_view);
                }
                return data_view;
              });
              $scope.selected_data_view = Object.assign({}, data.data_view);
              _init_data();
              _load_data();
              $scope.editing = false;
              return;
            }
            $scope.create_errors.push(data.message);
            for (let i in data.errors) {
              $scope.create_errors.push(data.errors[i]);
            }
            spinner_utility.hide();
        };

        if ($scope.selected_data_view.id) {
          let new_data_view = data_view_service.update_data_view($scope.selected_data_view.id, $scope.fields.name, checked_filter_groups, checked_cycles, aggregations).then(_done);
        } else {
          let new_data_view = data_view_service.create_data_view($scope.fields.name, checked_filter_groups, checked_cycles, aggregations).then(_done);
        };
      };

      $scope.click_cancel = function () {
        spinner_utility.show();
        $scope.selected_data_view = null;
        $scope.create_errors = [];
        _init_fields();
        _init_data();
        $scope.editing = false;
        spinner_utility.hide();
      };

      $scope.click_delete = function (data_view=null) {
        spinner_utility.show();
        if (!data_view) {
          data_view = $scope.selected_data_view
        }
        if (confirm('Are you sure to delete the data view "' + data_view.name + '"?')) {
          delete_id = data_view.id;
          let delete_data_view = data_view_service.delete_data_view(delete_id).then((data) => {
            if (data.status == 'success') {
                $scope.data_views = $scope.data_views.filter(data_view => data_view.id != delete_id);
                if ($scope.selected_data_view.id == data_view.id) {
                  window.location = '#/insights/custom';
                }
              }
            });
          };
        spinner_utility.hide();
      };

      $scope.click_edit = function () {
        spinner_utility.show();
        $scope.fields.name = $scope.selected_data_view.name;
        for (let i in $scope.selected_data_view.cycles) {
          $scope.fields.cycle_checkboxes[$scope.selected_data_view.cycles[i]] = true;
        }

        for (let i in $scope.selected_data_view.filter_groups) {
          $scope.fields.filter_group_checkboxes[$scope.selected_data_view.filter_groups[i]] = true;
        }
        $scope.editing = true;
        spinner_utility.hide();
      };
      // CHARTS
      var colors = [
        '#4477AA',
        '#DDDD77',
        '#77CCCC',
        '#117744',
        '#DD7788',
        '#AA4455',
        '#77AADD',
        '#44AAAA',
        '#AAAA44',
        '#114477',
        '#117777',
        '#771122',
        '#777711',
        '#AA7744',
        '#DDAA77',
        '#771155',
        '#AA4488',
        '#CC99BB',
        '#44AA77',
        '#88CCAA',
        '#774411',
      ]

      const _build_chart = () => {
        console.log('BUILD CHART')
        if (!$scope.data.graph_data) {
          console.log('NO DATA')
          spinner_utility.hide()
          return
        }
        const canvas = document.getElementById('data-view-chart')
        const ctx = canvas.getContext('2d')

        let first_axis_name = $scope.source_column_by_location.first_axis ? $scope.source_column_by_location.first_axis.displayName : 'y1'
        let second_axis_name = $scope.source_column_by_location.second_axis ? $scope.source_column_by_location.second_axis.displayName : 'y2'

        $scope.dataViewChart = new Chart(ctx, {
          type: 'line',
          data: {
          },
          options: {
            plugins: {
              title: {
                display: true,
                align: 'start'
              },
              legend: {
                position: 'right',
                maxWidth: 500,
                title: {
                  display: true,
                  text: "Solid Line (Left Axis) - Dashed Line (Right Axis)",
                },
                labels: {
                  boxHeight: 0,
                  boxWidth: 50,
                },
              },
            },
            scales: {
              y1: {
                beginAtZero: true,
                position: 'left',
                display: false,
                title: {
                  text: first_axis_name,
                  display: true,
                }
              },
              y2: {
                beginAtZero: true,
                position: 'right',
                display: false,
                title: {
                  text: second_axis_name,
                  display: false,
                }
              },

            }
          }
        })
        console.log('_assign_datasets BUILD CHART')
        _assign_datasets()
      }

      const _assign_datasets = () => {
        console.log('assgin dataset start')
        if (!$scope.data.graph_data) {
          spinner_utility.hide()
          return
        }
        xAxisLabels = $scope.data.graph_data.labels
        datasets = []
        axis1_aggregations = $scope.selected_data_view.first_axis_aggregations.map(agg1 => $scope.aggregations.find(agg2 => agg2.id == agg1).name)
        axis2_aggregations = $scope.selected_data_view.second_axis_aggregations.map(agg1 => $scope.aggregations.find(agg2 => agg2.id == agg1).name)
        if (axis1_aggregations.length > 0) {
          $scope.dataViewChart.options.scales.y1.display = true
        } else {
          $scope.dataViewChart.options.scales.y1.display = false
        }

        axis1_column = $scope.source_column_by_location.first_axis.column_name

        let i = 0
        for (let aggregation of axis1_aggregations) {
          for (let dataset of $scope.data.graph_data.datasets) {
            if (aggregation == dataset.aggregation && axis1_column == dataset.column && dataset.filter_group in $scope.selected_filter_groups) {
              dataset.label = `${dataset.filter_group} - ${dataset.column} - ${dataset.aggregation}`
              dataset.backgroundColor = colors[i],
              dataset.borderColor = colors[i],
              dataset.tension = 0.1
              dataset.yAxisID = 'y1'
              datasets.push(dataset)
              i = i > 19 ? 0 : i + 1
            }
          }
        }

        if ($scope.source_column_by_location.second_axis) {
          axis2_column = $scope.source_column_by_location.second_axis.column_name
          let second_axis_name = $scope.source_column_by_location.second_axis.displayName
          console.log('second axis name', second_axis_name)

          $scope.dataViewChart.options.scales.y2.display = true
          $scope.dataViewChart.options.scales.y2.title.text = second_axis_name
          $scope.dataViewChart.options.scales.y2.title.display = true

          console.log('axis 2 aggs', axis2_aggregations)
          for (let aggregation of axis2_aggregations) {
            for (let dataset of $scope.data.graph_data.datasets) {
              if (aggregation == dataset.aggregation && axis2_column == dataset.column && dataset.filter_group in $scope.selected_filter_groups) {
                dataset.label = `${dataset.filter_group} - ${dataset.column} - ${dataset.aggregation}`
                dataset.backgroundColor = colors[i],
                dataset.borderColor = colors[i],
                dataset.tension = 0.1
                dataset.yAxisID = 'y2'
                dataset.borderDash = [10,15]
                datasets.push(dataset)
                i = i > 19 ? 0 : i + 1
              }
            }
          }
        } else {
          $scope.dataViewChart.options.scales.y2.title.display = false
        }

        $scope.dataViewChart.data.labels = xAxisLabels
        $scope.dataViewChart.data.datasets = datasets
        $scope.dataViewChart.options.plugins.title.text = $scope.selected_data_view.name
        $scope.dataViewChart.update()
        console.log('_assign_data COMPLETE ')
      }

      _init_fields();
      _init_data();
      _load_data();
    }
  ]);
