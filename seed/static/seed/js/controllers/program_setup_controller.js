/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.program_setup', []).controller('program_setup_controller', [
  '$scope',
  '$stateParams',
  'compliance_metrics',
  'compliance_metric_service',
  'filter_groups',
  'Notification',
  'organization_payload',
  'property_columns',
  'spinner_utility',
  'x_axis_columns',
  function (
    $scope,
    $stateParams,
    compliance_metrics,
    compliance_metric_service,
    filter_groups,
    Notification,
    organization_payload,
    property_columns,
    spinner_utility,
    x_axis_columns
  ) {
    $scope.id = $stateParams.id;
    $scope.org = organization_payload.organization;
    $scope.compliance_metrics = compliance_metrics;
    $scope.new_compliance_metric = {};
    $scope.fields = {
      start_year: null,
      end_year: null
    };
    $scope.program_settings_not_changed = true;
    $scope.program_settings_changed = function () {
      $scope.program_settings_not_changed = false;
    };

    $scope.errors = [];
    if ($scope.compliance_metrics.length > 0) {
      $scope.new_compliance_metric = $scope.compliance_metrics[0]; // assign to first for now
      // truncate start and end dates to only show years YYYY
      $scope.fields.start_year = $scope.new_compliance_metric.start ? parseInt($scope.new_compliance_metric.start.split('-')[0]) : null;
      $scope.fields.end_year = $scope.new_compliance_metric.end ? parseInt($scope.new_compliance_metric.end.split('-')[0]) : null;

    }
    $scope.property_columns = property_columns;
    $scope.x_axis_columns = x_axis_columns;


    $scope.get_column_display = function (id) {
      let record = _.find($scope.property_columns, {id: id});
      if (record) {
        return record.displayName;
      }
    };

    $scope.get_x_axis_display = function (id) {
      let record = _.find($scope.x_axis_columns, {id: id});
      if (record) {
        return record.displayName;
      }
    };

    $scope.x_axis_selection = '';

    $scope.select_x_axis = function () {
      $scope.program_settings_not_changed = false;
      let selection = $scope.x_axis_selection;
      $scope.x_axis_selection = '';
      if (!$scope.new_compliance_metric.x_axis_columns) {
        $scope.new_compliance_metric.x_axis_columns = [];
      }
      if ($scope.new_compliance_metric.x_axis_columns.includes(selection)) {
        return;
      }
      $scope.new_compliance_metric.x_axis_columns.push(selection);
    };

    $scope.click_remove_x_axis = function (id) {
      $scope.program_settings_not_changed = false;
      $scope.new_compliance_metric.x_axis_columns = $scope.new_compliance_metric.x_axis_columns.filter(item => item != id);
    };

    // Filter Groups
    $scope.filter_groups = filter_groups;
    $scope.get_filter_group_display = function (id) {
      let record = _.find($scope.filter_groups, {id: id});
      if (record) {
        return record.name;
      }
    };

    let _init_data  = function () {
      // load compliance metrics
      $scope.compliance_metrics = compliance_metrics;
      $scope.has_compliance_metrics = $scope.compliance_metrics.length > 0;
      $scope.selected_compliance_metric = $scope.id ? $scope.compliance_metrics.find(item => item.id === $scope.id) : null;
      if ($scope.selected_compliance_metric) {
      } else if ($scope.id) {
        $scope.errors = 'Could not find Program Metric with id #' + $scope.id + '!';
      }
    };
    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.errors = [];
      if (!$scope.new_compliance_metric.name) {
        $scope.errors.push('A name is required!');
      }
      if (!$scope.fields.start_year) {
        $scope.errors.push('A compliance period start year (XXXX) is required!');
      }
      if (!$scope.fields.end_year) {
        $scope.errors.push('A compliance period end year (XXXX) is required!');
      }
      let has_energy_metric = $scope.new_compliance_metric.actual_energy_column && $scope.new_compliance_metric.energy_metric_type;
      let has_emission_metric = $scope.new_compliance_metric.actual_emission_column && $scope.new_compliance_metric.emission_metric_type;
      let no_energy_metric = $scope.new_compliance_metric.actual_energy_column && !$scope.new_compliance_metric.energy_metric_type;
      let no_emission_metric = $scope.new_compliance_metric.actual_emission_column && !$scope.new_compliance_metric.emission_metric_type;
      let actual_energy_column_not_boolean = $scope.new_compliance_metric.actual_energy_column && !$scope.new_compliance_metric.target_energy_column && _.find($scope.property_columns, {id: $scope.new_compliance_metric.actual_energy_column}).data_type != 'boolean';
      let actual_emission_column_not_boolean = $scope.new_compliance_metric.actual_emission_column && !$scope.new_compliance_metric.target_emission_column && _.find($scope.property_columns, {id: $scope.new_compliance_metric.actual_emission_column}).data_type != 'boolean';

      if ((!has_energy_metric && !has_emission_metric) || (no_energy_metric || no_emission_metric)) {
        $scope.errors.push('A completed energy or emission metric is required!');
      }
      if ($scope.new_compliance_metric.x_axis_columns.length < 1) {
        $scope.errors.push('At least one x-axis column is required!');
      }
      if (actual_energy_column_not_boolean || actual_emission_column_not_boolean) {
        $scope.errors.push('The actual energy or emission columns must have a \'boolean\' data type if there is not a corresponding target column selected!');
      }
      if (!$scope.new_compliance_metric.actual_energy_column && $scope.new_compliance_metric.target_energy_column || !$scope.new_compliance_metric.actual_emission_column && $scope.new_compliance_metric.target_emission_column) {
        $scope.errors.push('The actual energy or emission columns must be included when the target column is selected!');
      }
      if ($scope.errors.length > 0) {
        return;
      }

      // just for saving
      $scope.new_compliance_metric.start = $scope.fields.start_year + '-01-01';
      $scope.new_compliance_metric.end = $scope.fields.end_year + '-12-31';

      // need to use list compliance metric to see if one exists
      if ($scope.compliance_metrics.length > 0) {
        console.log("Existing metric");
        // update the compliance metric
        compliance_metric_service.update_compliance_metric($scope.compliance_metrics[0].id, $scope.new_compliance_metric).then(data => {
          if ('status' in data && data.status == 'error') {
            for (const [key, error] of Object.entries(data.errors)) {
              $scope.errors.push(key + ': ' + error);
            }
          } else {
            console.log(data, $scope.new_compliance_metric);
            $scope.new_compliance_metric = data;
            console.log($scope.new_compliance_metric);
            //reset for displaying
            $scope.new_compliance_metric.start = parseInt($scope.new_compliance_metric.start.split('-')[0]);
            $scope.new_compliance_metric.end = parseInt($scope.new_compliance_metric.end.split('-')[0]);
          }
        });

      } else {
        // create a new compliance metric
        compliance_metric_service.new_compliance_metric($scope.new_compliance_metric).then(data => {
          if ('status' in data && data.status == 'error') {
            for (const [key, error] of Object.entries(data.errors)) {
              $scope.errors.push(key + ': ' + error);
            }
          } else {
            $scope.new_compliance_metric = data;
            // reset for displaying
            $scope.new_compliance_metric.start = parseInt($scope.new_compliance_metric.start.split('-')[0]);
            $scope.new_compliance_metric.end = parseInt($scope.new_compliance_metric.end.split('-')[0]);
          }
        });
      }
      $scope.program_settings_not_changed = true;
      setTimeout(() => {
        Notification.primary('<a href="#/insights" style="color: #337ab7;">Click here to view your Program Overview</a>');
        Notification.success('Program Metric Configuration Saved!');
      }, 1000);
    };

    $scope.click_new_compliance_metric = function () {
      spinner_utility.show();
      $scope.selected_compliance_metric = {
        name: 'New Program Metric',
      };
      $scope.editing = true;
      spinner_utility.hide();
    };

    $scope.click_delete = function (compliance_metric=null) {
      spinner_utility.show();
      if (!compliance_metric) {
        compliance_metric = $scope.selected_compliance_metric;
      }
      if (confirm('Are you sure you want to delete the Program Metric "' + compliance_metric.name + '"?')) {
        delete_id = compliance_metric.id;
        let delete_compliance_metric = compliance_metric_service.delete_compliance_metric(delete_id).then((data) => {
          if (data.status == 'success') {
              $scope.compliance_metrics = $scope.compliance_metrics.filter(compliance_metric => compliance_metric.id != delete_id);
              if ($scope.selected_compliance_metric.id == compliance_metric.id) {
                window.location = '#/insights/custom';
              }
            }
          });
        };
      spinner_utility.hide();
    };

    _init_data();
  }]);
