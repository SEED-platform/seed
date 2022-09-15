/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.compliance_setup', []).controller('compliance_setup_controller', [
  '$scope',
  '$stateParams',
  'compliance_metrics',
  'compliance_metric_service',
  'organization_payload',
  'property_columns',
  function (
    $scope,
    $stateParams,
    compliance_metrics,
    compliance_metric_service,
    organization_payload,
    property_columns,
  ) {
    $scope.org = organization_payload.organization;
    $scope.complianceMetrics = compliance_metrics;
    console.log("compliancemetrics: ", $scope.complianceMetrics);
    $scope.new_compliance_metric = {};
    $scope.fields = {
      'start_year': null,
      'end_year': null
    }
    if ($scope.complianceMetrics.length > 0){
      $scope.new_compliance_metric = $scope.complianceMetrics[0];  // assign to first for now
      // truncate start and end dates to only show years YYYY
      $scope.fields.start_year = $scope.new_compliance_metric.start ? parseInt($scope.new_compliance_metric.start.split('-')[0]) : null
      $scope.fields.end_year = $scope.new_compliance_metric.end ? parseInt($scope.new_compliance_metric.end.split('-')[0]) : null

    }
    $scope.property_columns = property_columns;


    $scope.get_column_display = function (id) {
      let record = _.find($scope.property_columns, {'id': id});
      if (record) {
        return record.displayName;
      }
    };

    $scope.x_axis_selection = '';

    $scope.select_x_axis = function () {
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
      $scope.new_compliance_metric.x_axis_columns = $scope.new_compliance_metric.x_axis_columns.filter(item => item != id);
    };

    // $scope.energyMetricType = energyMetricType;
    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {

      // just for saving
      $scope.new_compliance_metric.start = $scope.fields.start_year + "-01-01";
      $scope.new_compliance_metric.end = $scope.fields.end_year + "-12-31";

      // need to use list compliance metric to see if one exists
      if ($scope.complianceMetrics.length > 0) {
        // update the compliance metric
        console.log('updating...', $scope.complianceMetrics[0])
        compliance_metric_service.update_compliance_metric($scope.complianceMetrics[0].id, $scope.new_compliance_metric).then(data => {
            if ('status' in data && data.status == 'error') {
              console.log("ERROR updating...")
            } else {
              console.log("metric updated!")
              $scope.new_compliance_metric = data;
              //reset for displaying
              $scope.new_compliance_metric.start = parseInt($scope.new_compliance_metric.start.split('-')[0]);
              $scope.new_compliance_metric.end = parseInt($scope.new_compliance_metric.end.split('-')[0]);
            }
        });

      } else {
        // create a new compliance metric
        console.log("creating new metric...", $scope.new_compliance_metric)
        compliance_metric_service.new_compliance_metric($scope.new_compliance_metric).then(data => {
              console.log(data)
              if ('status' in data and data.status == 'error') {
                console.log("ERROR saving...")
              } else {
                console.log("metric saved!")
                $scope.new_compliance_metric = data;
                // reset for displaying
                $scope.new_compliance_metric.start = parseInt($scope.new_compliance_metric.start.split('-')[0]);
                $scope.new_compliance_metric.end = parseInt($scope.new_compliance_metric.end.split('-')[0]);
              }
         });
      }
    };

  }]);
