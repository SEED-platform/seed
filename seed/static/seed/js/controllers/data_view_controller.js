/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_view', []).controller('data_view_controller', [
  '$scope',
  '$state',
  '$stateParams',
  '$uibModal',
  'urls',
  'auth_payload',
  'cycles',
  'data_views',
  'filter_groups',
  'data_view_service',
  'property_columns',
  'spinner_utility',
  'taxlot_columns',
  'valid_column_data_types',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $stateParams,
    $uibModal,
    urls,
    auth_payload,
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
    $scope.state = $state.current;
    $scope.id = $stateParams.id;
    $scope.valid_column_data_types = valid_column_data_types;
    $scope.editing = false;
    $scope.create_errors = [];
    $scope.data_views_error = null;
    $scope.cycles = cycles.cycles;
    $scope.auth = auth_payload.auth;
    $scope.fields = {
      filter_group_checkboxes: {},
      cycle_checkboxes: {},
      name: ''
    };
    $scope.show_properties_for_filter_group = {};
    $scope.aggregations = [
      { id: 1, name: 'Average' },
      { id: 2, name: 'Minimum' },
      { id: 3, name: 'Maximum' },
      { id: 4, name: 'Sum' },
      { id: 5, name: 'Count' }
    ];
    $scope.filter_groups = filter_groups;

    $scope.show_config = true;
    $scope.toggle_config = () => {
      $scope.show_config = !$scope.show_config;
    };

    const _collect_array_as_object = (array, key = 'id') => {
      const ret = {};
      for (const i in array) {
        ret[array[i][key]] = array[i];
      }
      return ret;
    };

    const _collect_array_as_object_sorted = (array, key = 'start') => {
      const ret = {};
      for (const i in array) {
        ret[array[i][key]] = array[i];
      }
      return ret;
    };

    const _init_fields = () => {
      for (const i in $scope.filter_groups) {
        $scope.fields.filter_group_checkboxes[$scope.filter_groups[i].id] = false;
      }
      for (const i in $scope.cycles) {
        $scope.fields.cycle_checkboxes[$scope.cycles[i].id] = false;
      }
      $scope.source_column_by_location = { first_axis: null, second_axis: null };
    };

    const _init_data = () => {
      // load data views
      $scope.data_views = data_views;
      if (data_views.status === 'error') {
        $scope.data_views_error = data_views.message;
      }
      $scope.has_data_views = $scope.data_views.length > 0;
      $scope.selected_data_view = $scope.id ? $scope.data_views.find((item) => item.id === $scope.id) : null;
      if ($scope.selected_data_view) {
        $scope.selected_data_view.first_axis_aggregations = [];
        $scope.selected_data_view.second_axis_aggregations = [];
        $scope.fields.name = $scope.selected_data_view.name;
      } else if ($scope.id) {
        $scope.data_views_error = `Could not find Data View with id #${$scope.id}!`;
      }

      // load cycles
      $scope.used_cycles = {};
      if ($scope.selected_data_view) {
        $scope.used_cycles = _collect_array_as_object_sorted($scope.cycles.filter((item) => $scope.selected_data_view.cycles.includes(item.id)));
      }
      $scope.selected_cycles = { ...$scope.used_cycles };
      $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;

      // load source columns
      $scope.source_columns = {
        property: property_columns,
        taxlot: taxlot_columns,
        by_id: Object.assign(_collect_array_as_object(property_columns), _collect_array_as_object(taxlot_columns))
      };

      // load both axis
      if ($scope.selected_data_view) {
        const first_axis_aggregations = $scope.selected_data_view.parameters.find((item) => item.location === 'first_axis');
        if (first_axis_aggregations) {
          $scope.selected_table_location = 'first_axis';
          $scope.selected_table_aggregation = first_axis_aggregations.aggregations[0];
          $scope.select_source_column('first_axis', first_axis_aggregations.column, false);
          for (const i in first_axis_aggregations.aggregations) {
            $scope.toggle_aggregation('first_axis', first_axis_aggregations.aggregations[i]);
          }
        }
        const second_axis_aggregations = $scope.selected_data_view.parameters.find((item) => item.location === 'second_axis');
        if (second_axis_aggregations) {
          $scope.select_source_column('second_axis', second_axis_aggregations.column, false);
          for (const i in second_axis_aggregations.aggregations) {
            $scope.toggle_aggregation('second_axis', second_axis_aggregations.aggregations[i]);
          }
        }
      }

      // load filter groups
      $scope.used_filter_groups = {};
      if ($scope.selected_data_view) {
        $scope.used_filter_groups = $scope.filter_groups
          .filter((fg) => $scope.selected_data_view.filter_groups.includes(fg.id))
          .reduce((acc, curr) => {
            acc[curr.name] = curr;
            return acc;
          }, {});
        for (const i in $scope.selected_data_view.filter_groups) {
          $scope.show_properties_for_filter_group[$scope.selected_data_view.filter_groups[i]] = false;
        }
      }
      $scope.selected_filter_groups = { ...$scope.used_filter_groups };
    };

    $scope.data = {};
    const _load_data = () => {
      if (!$scope.selected_data_view) {
        spinner_utility.hide();
        return;
      }
      spinner_utility.show();
      return data_view_service
        .evaluate_data_view(
          $scope.selected_data_view.id,
          Object.values($scope.source_column_by_location)
            .filter((item) => item)
            .map((item) => item.id)
        )
        .then((data) => {
          $scope.data = data;
          spinner_utility.hide();
        })
        .then(() => {
          _build_chart();
        });
    };

    $scope.object_has_key = (a, b) => Object.keys(a).includes(String(b));
    $scope.object_has_any_key = (a) => Object.keys(a).length > 0;

    $scope.toggle_filter_group = (filter_group_id) => {
      const filter_group = $scope.filter_groups.find((fg) => fg.id === filter_group_id);
      if (filter_group.name in $scope.selected_filter_groups) {
        delete $scope.selected_filter_groups[filter_group.name];
      } else {
        $scope.selected_filter_groups[filter_group.name] = { ...$scope.used_filter_groups[filter_group.name] };
      }
      $scope.click_edit();
      _assign_datasets();
    };

    $scope.toggle_cycle = (cycle_id) => {
      if (cycle_id in $scope.selected_cycles) {
        delete $scope.selected_cycles[cycle_id];
      } else {
        $scope.selected_cycles[cycle_id] = { ...$scope.used_cycles[cycle_id] };
      }
      $scope.selected_cycles_length = Object.keys($scope.selected_cycles).length;
      $scope.click_edit();
      _assign_datasets();
    };

    $scope.toggle_aggregation = (location, aggregation_id) => {
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
        $scope.click_edit();
        _assign_datasets();
      }
    };

    $scope.select_source_column = (location, source_column_id, reload_data = true) => {
      if (source_column_id) {
        $scope.source_column_by_location[location] = { ...$scope.source_columns.by_id[source_column_id] };
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
      if (reload_data) {
        _load_data();
        $scope.click_edit();
      }

      _assign_datasets();
    };

    $scope.click_new_data_view = () => {
      spinner_utility.show();
      $scope.selected_data_view = {
        name: 'New Custom Report',
        first_axis_aggregations: [],
        second_axis_aggregations: [],
        filter_groups: [],
        cycles: []
      };
      $scope.editing = true;
      $scope.fields.name = $scope.selected_data_view.name;
      spinner_utility.hide();
    };

    $scope.click_save_changes = () => {
      spinner_utility.show();
      $scope.create_errors = [];

      // validate name
      if (!$scope.fields.name) {
        $scope.create_errors.push('A name is required.');
      }

      // validate filter groups
      const checked_filter_groups = [];
      for (const i in $scope.fields.filter_group_checkboxes) {
        if ($scope.fields.filter_group_checkboxes[i]) {
          checked_filter_groups.push(parseInt(i, 10));
        }
      }
      if (checked_filter_groups.length < 1) {
        $scope.create_errors.push('At least one filter group must be selected.');
      }

      // validate cycles
      const checked_cycles = [];
      for (const i in $scope.fields.cycle_checkboxes) {
        if ($scope.fields.cycle_checkboxes[i]) {
          checked_cycles.push(parseInt(i, 10));
        }
      }
      if (checked_cycles.length < 1) {
        $scope.create_errors.push('At least one cycle must be selected.');
      }

      // validate column
      if (!$scope.source_column_by_location.first_axis) {
        $scope.create_errors.push('The first axis must have a source column.');
      }
      if ($scope.selected_data_view.first_axis_aggregations.length < 1) {
        $scope.create_errors.push('The first axis needs at least one selected aggregation.');
      }
      if ($scope.source_column_by_location.second_axis && $scope.selected_data_view.second_axis_aggregations.length < 1) {
        $scope.create_errors.push('The second axis needs at least one selected aggregation.');
      }

      // any errors?
      if ($scope.create_errors.length > 0) {
        spinner_utility.hide();
        return;
      }

      // create/update data view
      const aggregations = [];
      if ($scope.source_column_by_location.first_axis) {
        aggregations.push({
          column: $scope.source_column_by_location.first_axis.id,
          location: 'first_axis',
          aggregations: $scope.selected_data_view.first_axis_aggregations
        });
      }
      if ($scope.source_column_by_location.second_axis) {
        aggregations.push({
          column: $scope.source_column_by_location.second_axis.id,
          location: 'second_axis',
          aggregations: $scope.selected_data_view.second_axis_aggregations
        });
      }

      const _done = (data) => {
        if (data.status === 'success') {
          if (!$scope.selected_data_view.id) {
            window.location = `#/insights/custom/${data.data_view.id}`;
            spinner_utility.hide();
            return;
          }
          data_views = data_views.map((data_view) => {
            if (data_view.id === data.data_view.id) {
              return { ...data.data_view };
            }
            return data_view;
          });
          $scope.selected_data_view = { ...data.data_view };
          _init_data();
          _load_data();
          $scope.editing = false;
          return;
        }
        $scope.create_errors.push(data.message);
        for (const error of data.errors) {
          $scope.create_errors.push(error);
        }
      };

      if ($scope.selected_data_view.id) {
        data_view_service.update_data_view($scope.selected_data_view.id, $scope.fields.name, checked_filter_groups, checked_cycles, aggregations).then(_done).finally(spinner_utility.hide);
      } else {
        data_view_service.create_data_view($scope.fields.name, checked_filter_groups, checked_cycles, aggregations).then(_done).finally(spinner_utility.hide);
      }
    };

    $scope.click_cancel = () => {
      spinner_utility.show();
      $scope.selected_data_view = null;
      $scope.create_errors = [];
      _init_fields();
      _init_data();
      $scope.editing = false;
      spinner_utility.hide();
    };

    $scope.click_delete = (data_view) => {
      spinner_utility.show();

      // if new data_view, just click cancel
      if (data_view.id === undefined) {
        $scope.click_cancel();
        return;
      }

      if (confirm(`Are you sure to delete the data view "${data_view.name}"?`)) {
        const delete_id = data_view.id;
        data_view_service.delete_data_view(delete_id).then((data) => {
          if (data.status === 'success') {
            $scope.data_views = $scope.data_views.filter((data_view) => data_view.id !== delete_id);
            if ($scope.selected_data_view.id === data_view.id) {
              window.location = '#/insights/custom';
            }
          }
        });
      }
      spinner_utility.hide();
    };

    $scope.click_edit = () => {
      spinner_utility.show();
      $scope.fields.name = $scope.selected_data_view.name;
      for (const cycleId of $scope.selected_data_view.cycles) {
        $scope.fields.cycle_checkboxes[cycleId] = true;
      }

      for (const filterGroupId of $scope.selected_data_view.filter_groups) {
        $scope.fields.filter_group_checkboxes[filterGroupId] = true;
      }
      $scope.editing = true;
      spinner_utility.hide();
    };
    // CHARTS
    const colors = [
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
      '#774411'
    ];
    const colorsByLabelPrefix = {};
    const colorIter = colors[Symbol.iterator]();
    for (const agg of $scope.aggregations) {
      for (const fg of $scope.filter_groups) {
        colorsByLabelPrefix[`${fg.name} - ${agg.name}`] = colorIter.next().value;
      }
    }

    const _build_chart = () => {
      if (!$scope.data.graph_data) {
        spinner_utility.hide();
        return;
      }
      const canvas = document.getElementById('data-view-chart');
      const ctx = canvas.getContext('2d');

      const first_axis_name = $scope.source_column_by_location.first_axis ? $scope.source_column_by_location.first_axis.displayName : 'y1';
      const second_axis_name = $scope.source_column_by_location.second_axis ? $scope.source_column_by_location.second_axis.displayName : 'y2';

      $scope.dataViewChart = new Chart(ctx, {
        type: 'line',
        data: {},
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
                text: 'Solid Line (Left Axis) - Dashed Line (Right Axis)'
              },
              labels: {
                boxHeight: 0,
                boxWidth: 50,
                sort: (a, b) => a.text.localeCompare(b.text) // alphabetical
              }
            }
          },
          scales: {
            y1: {
              beginAtZero: true,
              position: 'left',
              display: false,
              title: {
                text: first_axis_name,
                display: true
              }
            },
            y2: {
              beginAtZero: true,
              position: 'right',
              display: false,
              title: {
                text: second_axis_name,
                display: false
              }
            }
          }
        }
      });
      _assign_datasets();
    };

    $scope.downloadChart = () => {
      const a = document.createElement('a');
      a.href = $scope.dataViewChart.toBase64Image();
      a.download = 'Custom Report.png';
      a.click();
    };

    const _assign_datasets = () => {
      if (!$scope.data.graph_data) {
        spinner_utility.hide();
        return;
      }

      const xAxisLabels = $scope.data.graph_data.labels;
      const selectedCycleNames = Object.values($scope.selected_cycles).map((c) => c.name);
      const xAxisLabelsSelected = xAxisLabels.map((l) => selectedCycleNames.includes(l));
      const xAxisLabelsSelectedMask = (_, i) => xAxisLabelsSelected[i];

      const datasets = [];
      const axis1_aggregations = $scope.selected_data_view.first_axis_aggregations.map((agg1) => $scope.aggregations.find((agg2) => agg2.id == agg1).name);
      const axis2_aggregations = $scope.selected_data_view.second_axis_aggregations.map((agg1) => $scope.aggregations.find((agg2) => agg2.id == agg1).name);
      $scope.dataViewChart.options.scales.y1.display = axis1_aggregations.length > 0;

      const axis1_column = $scope.source_column_by_location.first_axis.displayName;
      let i = 0;
      for (const aggregation of axis1_aggregations) {
        for (const dataset of $scope.data.graph_data.datasets) {
          const columnWithUnits = new RegExp(`^${dataset.column}( \(.+?\))?$`);
          if (aggregation === dataset.aggregation && columnWithUnits.test(axis1_column) && dataset.filter_group in $scope.selected_filter_groups) {
            dataset.label = `${dataset.filter_group} - ${dataset.aggregation} - ${dataset.column}`;
            const color = colorsByLabelPrefix[`${dataset.filter_group} - ${dataset.aggregation}`];
            dataset.backgroundColor = color;
            dataset.borderColor = color;
            dataset.tension = 0.1;
            dataset.yAxisID = 'y1';
            // spread in data filter so the object itself is not modified.
            datasets.push({ ...dataset, data: dataset.data.filter(xAxisLabelsSelectedMask) });
            i = i > 19 ? 0 : i + 1;
          }
        }
      }

      if ($scope.source_column_by_location.second_axis) {
        i = 0;
        const axis2_column = $scope.source_column_by_location.second_axis.displayName;
        const second_axis_name = $scope.source_column_by_location.second_axis.displayName;

        $scope.dataViewChart.options.scales.y2.display = true;
        $scope.dataViewChart.options.scales.y2.title.text = second_axis_name;
        $scope.dataViewChart.options.scales.y2.title.display = true;

        for (const aggregation of axis2_aggregations) {
          for (const dataset of $scope.data.graph_data.datasets) {
            const columnWithUnits = new RegExp(`^${dataset.column}( \(.+?\))?$`);
            if (aggregation === dataset.aggregation && columnWithUnits.test(axis2_column) && dataset.filter_group in $scope.selected_filter_groups) {
              dataset.label = `${dataset.filter_group} - ${dataset.aggregation} - ${dataset.column}`;
              const color = colorsByLabelPrefix[`${dataset.filter_group} - ${dataset.aggregation}`];
              dataset.backgroundColor = color;
              dataset.borderColor = color;
              dataset.tension = 0.1;
              dataset.yAxisID = 'y2';
              dataset.borderDash = [10, 15];
              // spread in data filter so the object itself is not modified.
              datasets.push({ ...dataset, data: dataset.data.filter(xAxisLabelsSelectedMask) });
              i = i > 19 ? 0 : i + 1;
            }
          }
        }
      } else {
        $scope.dataViewChart.options.scales.y2.title.display = false;
      }

      const yMax = Math.max(...datasets.map((d) => Math.max(...d.data)));
      $scope.dataViewChart.options.scales.y1.max = Math.trunc(1.1 * yMax);
      $scope.dataViewChart.options.scales.y2.max = Math.trunc(1.1 * yMax);
      $scope.dataViewChart.data.labels = xAxisLabels.filter(xAxisLabelsSelectedMask);
      $scope.dataViewChart.data.datasets = datasets;
      $scope.dataViewChart.options.plugins.title.text = $scope.selected_data_view.name;
      $scope.dataViewChart.update();
    };

    _init_fields();
    _init_data();
    _load_data();
  }
]);
