/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.compliance_setup', []).controller('compliance_setup_controller', [
  '$scope',
  '$stateParams',
  'compliance_metrics',
  'compliance_metric_service',
  'property_columns',
  function (
    $scope,
    $stateParams,
    compliance_metrics,
    compliance_metric_service,
    property_columns,
  ) {

    $scope.complianceMetrics = compliance_metrics;
    console.log("compliancemetrics: ", $scope.complianceMetrics);
    $scope.new_compliance_metric = {};
    if ($scope.complianceMetrics.length > 0){
      $scope.new_compliance_metric = $scope.complianceMetrics[0];  // assign to first for now
      // truncate start and end dates to only show years YYYY
      $scope.new_compliance_metric.start = $scope.new_compliance_metric.start ? $scope.new_compliance_metric.start.split('-')[0] : null
      $scope.new_compliance_metric.end = $scope.new_compliance_metric.end ? $scope.new_compliance_metric.end.split('-')[0] : null

    }
    $scope.property_columns = property_columns;
    // $scope.energyMetricType = energyMetricType;
    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {

      // just for saving
      $scope.new_compliance_metric.start = $scope.new_compliance_metric.start + "-01-01";
      $scope.new_compliance_metric.end = $scope.new_compliance_metric.end + "-12-31";

      // need to use list compliance metric to see if one exists
      if ($scope.complianceMetrics.length > 0) {
        // update the compliance metric
        console.log('updating...')
        compliance_metric_service.update_compliance_metric($scope.complianceMetrics[0].id, $scope.new_compliance_metric)
        .then(
          function (data) {
            console.log(data)
            if (_.includes(data, 'status')) {
              console.log("ERROR updating...")
            } else {
              console.log("metric updated!")
              $scope.new_compliance_metric = data;
              //reset for displaying
              $scope.new_compliance_metric.start = $scope.new_compliance_metric.start.split('-')[0];
              $scope.new_compliance_metric.end = $scope.new_compliance_metric.end.split('-')[0];
            }
        });

      } else {
        // create a new compliance metric
        console.log("creating new metric...")
        compliance_metric_service.new_compliance_metric($scope.new_compliance_metric)
        .then(
          function(data) {
              console.log(data)
              if (_.includes(data, 'status')) {
                console.log("ERROR saving...")
              } else {
                console.log("metric saved!")
                $scope.new_compliance_metric = data;
                // reset for displaying
                $scope.new_compliance_metric.start = $scope.new_compliance_metric.start.split('-')[0];
                $scope.new_compliance_metric.end = $scope.new_compliance_metric.end.split('-')[0];
              }
         });
      }
    };

  }]);
