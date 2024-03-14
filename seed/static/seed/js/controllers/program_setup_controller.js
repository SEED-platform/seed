/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.program_setup', []).controller('program_setup_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'compliance_metric_service',
  'Notification',
  'spinner_utility',
  'naturalSort',
  'cycles',
  'compliance_metrics',
  'organization_payload',
  'filter_groups',
  'property_columns',
  'id',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    compliance_metric_service,
    Notification,
    spinner_utility,
    naturalSort,
    cycles,
    compliance_metrics,
    organization_payload,
    filter_groups,
    property_columns,
    id
  ) {
    // spinner_utility.show();
    $scope.state = $state.current;
    $scope.org = organization_payload;
    $scope.cycles = cycles;
    $scope.id = id;
    $scope.filter_groups = filter_groups;
    // order cycles by start date
    $scope.cycles = _.orderBy($scope.cycles, ['start'], ['asc']);
    $scope.filter_groups = filter_groups;
    $scope.valid_column_data_types = ['number', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean'];
    $scope.valid_x_axis_data_types = ['number', 'string', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean'];

    $scope.property_columns = _.reject(property_columns, (item) => item.related || !$scope.valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
    $scope.x_axis_columns = _.reject(property_columns, (item) => item.related || !$scope.valid_x_axis_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
    $scope.x_axis_selection = '';
    $scope.cycle_selection = '';
    $scope.compliance_metrics_error = [];
    $scope.program_settings_not_changed = true;
    $scope.program_settings_changed = () => {
      $scope.program_settings_not_changed = false;
    };
    $scope.compliance_metrics = compliance_metrics;
    $scope.has_compliance_metrics = $scope.compliance_metrics.length > 0;
    $scope.selected_compliance_metric = null;

    // init_selected_compliance_metric (handle case where there are none)
    $scope.init_selected_metric = (id) => {
      $scope.has_compliance_metrics = $scope.compliance_metrics.length > 0;
      $scope.selected_compliance_metric = null;
      $scope.available_cycles = [];
      $scope.available_x_axis_columns = [];
      $scope.compliance_metrics_error = [];
      $scope.program_settings_not_changed = true;
      $scope.x_axis_selection = '';
      $scope.cycle_selection = '';
      $scope.available_x_axis_columns = () => [];
      $scope.available_cycles = () => [];

      if (id === null) {
        if ($scope.has_compliance_metrics) {
          // this is after a delete. choose the first metric?
          id = $scope.compliance_metrics[0].id;
        }
      }
      if (id != null) {
        $scope.selected_compliance_metric = $scope.compliance_metrics.find((item) => item.id === id);
      }
      $scope.available_x_axis_columns = () => $scope.x_axis_columns.filter(({ id }) => !$scope.selected_compliance_metric?.x_axis_columns.includes(id));
      $scope.available_cycles = () => $scope.cycles.filter(({ id }) => !$scope.selected_compliance_metric?.cycles.includes(id));
    };

    $scope.init_selected_metric($scope.id);

    $scope.get_column_display = (id) => {
      const record = _.find($scope.property_columns, { id });
      if (record) {
        return record.displayName;
      }
    };

    // cycles
    $scope.get_cycle_display = (id) => {
      const record = _.find($scope.cycles, { id });
      if (record) {
        return record.name;
      }
    };

    $scope.select_cycle = () => {
      $scope.program_settings_changed();
      const selection = $scope.cycle_selection;
      $scope.cycle_selection = '';
      if (!$scope.selected_compliance_metric.cycles) {
        $scope.selected_compliance_metric.cycles = [];
      }
      $scope.selected_compliance_metric.cycles.push(selection);
      $scope.order_selected_cycles();
    };

    $scope.order_selected_cycles = () => {
      // keep chronological order of displayed cycles
      $scope.selected_compliance_metric.cycles = _.map($scope.cycles.filter(({ id }) => $scope.selected_compliance_metric?.cycles.includes(id)), 'id');
    };

    $scope.click_remove_cycle = (id) => {
      $scope.program_settings_changed();
      $scope.selected_compliance_metric.cycles = $scope.selected_compliance_metric.cycles.filter((item) => item !== id);
    };

    // x-axes
    $scope.get_x_axis_display = (id) => {
      const record = _.find($scope.x_axis_columns, { id });
      if (record) {
        return record.displayName;
      }
    };

    $scope.select_x_axis = () => {
      $scope.program_settings_changed();
      const selection = $scope.x_axis_selection;
      $scope.x_axis_selection = '';
      if (!$scope.selected_compliance_metric.x_axis_columns) {
        $scope.selected_compliance_metric.x_axis_columns = [];
      }
      $scope.selected_compliance_metric.x_axis_columns.push(selection);
    };

    $scope.click_remove_x_axis = (id) => {
      $scope.program_settings_changed();
      $scope.selected_compliance_metric.x_axis_columns = $scope.selected_compliance_metric.x_axis_columns.filter((item) => item != id);
    };

    // Filter Groups
    $scope.get_filter_group_display = (id) => {
      const record = _.find($scope.filter_groups, { id });
      if (record) {
        return record.name;
      }
    };

    $scope.set_program = (id) => {
      // check to ensure there are no unsaved changes
      if ($scope.program_settings_not_changed) {
        // switch it out / re-init
        $scope.init_selected_metric(id);
      } else {
        // warn user to save first
        Notification.warning({ message: 'You have unsaved changes to the current program. Save your changes first before selecting a different program to update.', delay: 5000 });
      }
    };

    /**
     * saves the updated settings
     */
    $scope.save_settings = () => {
      spinner_utility.show();
      $scope.compliance_metrics_error = [];
      if (!$scope.selected_compliance_metric.name) {
        $scope.compliance_metrics_error.push('A name is required!');
      }
      if ($scope.selected_compliance_metric.cycles) {
        if ($scope.selected_compliance_metric.cycles.length < 1) {
          $scope.compliance_metrics_error.push('At least one cycle is required!');
        }
      }
      const has_energy_metric = $scope.selected_compliance_metric.actual_energy_column && $scope.selected_compliance_metric.energy_metric_type;
      const has_emission_metric = $scope.selected_compliance_metric.actual_emission_column && $scope.selected_compliance_metric.emission_metric_type;
      const no_energy_metric = $scope.selected_compliance_metric.actual_energy_column && !$scope.selected_compliance_metric.energy_metric_type;
      const no_emission_metric = $scope.selected_compliance_metric.actual_emission_column && !$scope.selected_compliance_metric.emission_metric_type;
      const actual_energy_column_not_boolean =
        $scope.selected_compliance_metric.actual_energy_column &&
        !$scope.selected_compliance_metric.target_energy_column &&
        _.find($scope.property_columns, { id: $scope.selected_compliance_metric.actual_energy_column }).data_type !== 'boolean';
      const actual_emission_column_not_boolean =
        $scope.selected_compliance_metric.actual_emission_column &&
        !$scope.selected_compliance_metric.target_emission_column &&
        _.find($scope.property_columns, { id: $scope.selected_compliance_metric.actual_emission_column }).data_type !== 'boolean';

      if ((!has_energy_metric && !has_emission_metric) || no_energy_metric || no_emission_metric) {
        $scope.compliance_metrics_error.push('A completed energy or emission metric is required!');
      }
      if ($scope.selected_compliance_metric.x_axis_columns) {
        if ($scope.selected_compliance_metric.x_axis_columns.length < 1) {
          $scope.compliance_metrics_error.push('At least one x-axis column is required!');
        }
      }
      if (actual_energy_column_not_boolean || actual_emission_column_not_boolean) {
        $scope.compliance_metrics_error.push("The actual energy or emission columns must have a 'boolean' data type if there is not a corresponding target column selected!");
      }
      if (
        (!$scope.selected_compliance_metric.actual_energy_column && $scope.selected_compliance_metric.target_energy_column) ||
        (!$scope.selected_compliance_metric.actual_emission_column && $scope.selected_compliance_metric.target_emission_column)
      ) {
        $scope.compliance_metrics_error.push('The actual energy or emission columns must be included when the target column is selected!');
      }
      if ($scope.compliance_metrics_error.length > 0) {
        spinner_utility.hide();
        return;
      }

      if ($scope.selected_compliance_metric.id) {
        // update the compliance metric
        compliance_metric_service.update_compliance_metric($scope.selected_compliance_metric.id, $scope.selected_compliance_metric, $scope.org.id).then((data) => {
          if ('status' in data && data.status === 'error') {
            for (const [key, error] of Object.entries(data.compliance_metrics_error)) {
              $scope.compliance_metrics_error.push(`${key}: ${error}`);
            }
          } else {
            // success. the ID would already be saved so this block seems unnecessary
            if (!$scope.selected_compliance_metric.id) {
              $scope.selected_compliance_metric.id = data.id;
            }
            // replace data into compliance metric
            const index = _.findIndex($scope.compliance_metrics, ['id', data.id]);
            if (index >= 0) {
              $scope.compliance_metrics[index] = data;
            } else {
              $scope.compliance_metrics.push(data);
            }
            $scope.selected_compliance_metric = data;
          }
        });
      } else {
        // create the compliance metric
        compliance_metric_service.new_compliance_metric($scope.selected_compliance_metric, $scope.org.id).then((data) => {
          $scope.compliance_metrics.push(data);
          $scope.init_selected_metric(data.id);
        });
      }

      // display messages
      // Notification.primary({ message: '<a href="#/insights" style="color: #337ab7;">Click here to view your Program Overview</a>', delay: 5000 });
      Notification.success({ message: 'Program Setup Saved!', delay: 5000 });

      $scope.program_settings_not_changed = true;
      spinner_utility.hide();
    };

    $scope.click_new_compliance_metric = () => {
      //spinner_utility.show();

      // create a new metric using api and then assign it to selected_compliance_metric that
      // way it will have an id
      $scope.selected_compliance_metric = {
        name: 'New Program',
        cycles: [],
        actual_energy_column: null,
        target_energy_column: null,
        energy_metric_type: '',
        actual_emission_column: null,
        target_emission_column: null,
        emission_metric_type: '',
        filter_group: null,
        x_axis_columns: []
      };
      //spinner_utility.hide();
    }

    $scope.click_delete = (compliance_metric = null) => {
      // spinner_utility.show();
      if (!compliance_metric) {
        compliance_metric = $scope.selected_compliance_metric;
      }
      if (confirm(`Are you sure you want to delete the Program Metric "${compliance_metric.name}"?`)) {
        const delete_id = compliance_metric.id;
        compliance_metric_service.delete_compliance_metric(delete_id, $scope.org.id).then((data) => {
          if (data.status === 'success') {
            $scope.compliance_metrics = $scope.compliance_metrics.filter((compliance_metric) => compliance_metric.id !== delete_id);
            if ($scope.selected_compliance_metric.id === delete_id) {
              // notification
              Notification.success({ message: 'Compliance metric deleted successfully!', delay: 5000 });
              // reset selection
              $scope.selected_compliance_metric = {};
              $scope.init_selected_metric(null);
            }
          }
        });
      }
      // spinner_utility.hide();
    };

    $scope.close = () => {
      // close and return selected compliance metric
      $uibModalInstance.close($scope.selected_compliance_metric);
    };
  }
]);
