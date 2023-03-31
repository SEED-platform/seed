/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.program_setup', []).controller('program_setup_controller', [
  '$scope',
  '$state',
  '$stateParams',
  'compliance_metrics',
  'compliance_metric_service',
  'filter_groups',
  'Notification',
  'organization_payload',
  'cycles_payload',
  'property_columns',
  'spinner_utility',
  'x_axis_columns',
  function (
    $scope,
    $state,
    $stateParams,
    compliance_metrics,
    compliance_metric_service,
    filter_groups,
    Notification,
    organization_payload,
    cycles_payload,
    property_columns,
    spinner_utility,
    x_axis_columns
  ) {
    spinner_utility.show();
    $scope.state = $state.current;
    $scope.id = $stateParams.id;
    $scope.org = organization_payload.organization;
    $scope.cycles = cycles_payload.cycles;
    $scope.compliance_metrics_error = [];
    $scope.program_settings_not_changed = true;
    $scope.program_settings_changed = function () {
      $scope.program_settings_not_changed = false;
    };
    $scope.compliance_metrics = compliance_metrics;
    $scope.has_compliance_metrics = $scope.compliance_metrics.length > 0;

    if ($scope.id) {
      $scope.selected_compliance_metric = $scope.compliance_metrics.find(item => item.id === $scope.id);
    }
    $scope.property_columns = property_columns;
    $scope.x_axis_columns = x_axis_columns;

    $scope.get_column_display = function (id) {
      let record = _.find($scope.property_columns, {id: id});
      if (record) {
        return record.displayName;
      }
    };

    // cycles
    $scope.cycle_selection = '';
    $scope.get_cycle_display = function (id) {
      let record = _.find($scope.cycles, {id: id});
      if (record) {
        return record.name;
      }
    };

    $scope.available_cycles = () => {
      return $scope.cycles.filter(({id}) => !$scope.selected_compliance_metric?.cycles.includes(id));
    }

    $scope.select_cycle = function () {
      $scope.program_settings_changed();
      let selection = $scope.cycle_selection;
      $scope.cycle_selection = '';
      if (!$scope.selected_compliance_metric.cycles) {
        $scope.selected_compliance_metric.cycles = [];
      }
      $scope.selected_compliance_metric.cycles.push(selection);
    };

    $scope.click_remove_cycle = function (id) {
      $scope.program_settings_changed();
      $scope.selected_compliance_metric.cycles = $scope.selected_compliance_metric.cycles.filter(item => item != id);
    };

    // x-axes
    $scope.get_x_axis_display = function (id) {
      let record = _.find($scope.x_axis_columns, {id: id});
      if (record) {
        return record.displayName;
      }
    };

    $scope.available_x_axis_columns = () => {
      return $scope.x_axis_columns.filter(({id}) => !$scope.selected_compliance_metric?.x_axis_columns.includes(id));
    }

    $scope.x_axis_selection = '';

    $scope.select_x_axis = function () {
      $scope.program_settings_changed();
      let selection = $scope.x_axis_selection;
      $scope.x_axis_selection = '';
      if (!$scope.selected_compliance_metric.x_axis_columns) {
        $scope.selected_compliance_metric.x_axis_columns = [];
      }
      $scope.selected_compliance_metric.x_axis_columns.push(selection);
    };

    $scope.click_remove_x_axis = function (id) {
      $scope.program_settings_changed();
      $scope.selected_compliance_metric.x_axis_columns = $scope.selected_compliance_metric.x_axis_columns.filter(item => item != id);
    };

    // Filter Groups
    $scope.filter_groups = filter_groups;
    $scope.get_filter_group_display = function (id) {
      let record = _.find($scope.filter_groups, {id: id});
      if (record) {
        return record.name;
      }
    };


    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
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
      let has_energy_metric = $scope.selected_compliance_metric.actual_energy_column && $scope.selected_compliance_metric.energy_metric_type;
      let has_emission_metric = $scope.selected_compliance_metric.actual_emission_column && $scope.selected_compliance_metric.emission_metric_type;
      let no_energy_metric = $scope.selected_compliance_metric.actual_energy_column && !$scope.selected_compliance_metric.energy_metric_type;
      let no_emission_metric = $scope.selected_compliance_metric.actual_emission_column && !$scope.selected_compliance_metric.emission_metric_type;
      let actual_energy_column_not_boolean = $scope.selected_compliance_metric.actual_energy_column && !$scope.selected_compliance_metric.target_energy_column && _.find($scope.property_columns, {id: $scope.selected_compliance_metric.actual_energy_column}).data_type != 'boolean';
      let actual_emission_column_not_boolean = $scope.selected_compliance_metric.actual_emission_column && !$scope.selected_compliance_metric.target_emission_column && _.find($scope.property_columns, {id: $scope.selected_compliance_metric.actual_emission_column}).data_type != 'boolean';

      if ((!has_energy_metric && !has_emission_metric) || (no_energy_metric || no_emission_metric)) {
        $scope.compliance_metrics_error.push('A completed energy or emission metric is required!');
      }
      if ($scope.selected_compliance_metric.x_axis_columns) {
        if ($scope.selected_compliance_metric.x_axis_columns.length < 1) {
          $scope.compliance_metrics_error.push('At least one x-axis column is required!');
        }
      }
      if (actual_energy_column_not_boolean || actual_emission_column_not_boolean) {
        $scope.compliance_metrics_error.push('The actual energy or emission columns must have a \'boolean\' data type if there is not a corresponding target column selected!');
      }
      if (!$scope.selected_compliance_metric.actual_energy_column && $scope.selected_compliance_metric.target_energy_column || !$scope.selected_compliance_metric.actual_emission_column && $scope.selected_compliance_metric.target_emission_column) {
        $scope.compliance_metrics_error.push('The actual energy or emission columns must be included when the target column is selected!');
      }
      if ($scope.compliance_metrics_error.length > 0) {
        console.log("exited due to compliance_metrics_error");
        spinner_utility.hide();
        return;
      }

      // update the compliance metric
      console.log("about to update the metric");
      compliance_metric_service.update_compliance_metric($scope.selected_compliance_metric.id, $scope.selected_compliance_metric, $scope.org.id).then(data => {
        if ('status' in data && data.status == 'error') {
          for (const [key, error] of Object.entries(data.compliance_metrics_error)) {
            $scope.compliance_metrics_error.push(key + ': ' + error);
          }
        } else {
          if (!$scope.selected_compliance_metric.id) {
            window.location =
              '#/accounts/' +
              $scope.org.id +
              '/program_setup/' +
              data.id;
          }

          // replace data into compliance metric? needed?
          let index = _.findIndex($scope.compliance_metrics, ['id', data.id]);
          $scope.compliance_metrics[index] = data;

          $scope.selected_compliance_metric = data;

          window.location =
          '#/accounts/' +
          $scope.org.id +
          '/program_setup';

          return;
        }
      });

      // display messages
      Notification.primary({message: '<a href="#/insights" style="color: #337ab7;">Click here to view your Program Overview</a>', delay: 5000});
      Notification.success({message: 'Program Setup Saved!', delay: 5000});

      $scope.program_settings_not_changed = true;
      spinner_utility.hide();

    };

    $scope.click_new_compliance_metric = function () {
      spinner_utility.show();

      // create a new metric using api and then assign it to selected_compliance_metric that
      // way it will have an id
      let template_compliance_metric = {
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
      compliance_metric_service.new_compliance_metric(template_compliance_metric, $scope.org.id).then(data => {
        $scope.selected_compliance_metric = data;
        window.location =
        '#/accounts/' +
        $scope.org.id +
        '/program_setup/' +
        data.id;
      });
      $scope.program_settings_not_changed = true;

      spinner_utility.hide();
    };

    $scope.click_delete = function (compliance_metric = null) {
      spinner_utility.show();
      if (!compliance_metric) {
        compliance_metric = $scope.selected_compliance_metric;
      }
      if (confirm('Are you sure you want to delete the Program Metric "' + compliance_metric.name + '"?')) {
        let delete_id = compliance_metric.id;
        compliance_metric_service.delete_compliance_metric(delete_id, $scope.org.id).then((data) => {
          if (data.status == 'success') {
            $scope.compliance_metrics = $scope.compliance_metrics.filter(compliance_metric => compliance_metric.id != delete_id);
            if ($scope.selected_compliance_metric.id == delete_id) {
              window.location = '#/accounts/' + $scope.org.id + '/program_setup';
            }
          }
        });
      }
      spinner_utility.hide();
    };

  }]);
