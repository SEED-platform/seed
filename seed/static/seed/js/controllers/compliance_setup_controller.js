/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.compliance_setup', []).controller('compliance_setup_controller', [
  '$scope',
  '$stateParams',
  'compliance_metrics',
  'compliance_metric_service',
  function (
    $scope,
    $stateParams,
    compliance_metrics,
    compliance_metric_service,
  ) {

    $scope.complianceMetrics = compliance_metrics;
    $scope.new_compliance_metric = {};

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.new_compliance_metric.start = $scope.startYearValue + ":01:01";
      $scope.new_compliance_metric.end = $scope.endYearValue + ":12:31";
  
      // need to use list compliance metric to see if one exists
      if ($scope.complianceMetrics.length > 0) {
        // update the compliance metric
        compliance_metric_service.update_compliance_metric($scope.complianceMetrics[0].id, $scope.new_compliance_metric);
      } else {
        // create a new compliance metric
        compliance_metric_service.new_compliance_metric($scope.new_compliance_metric);
      }
    };

  }]);
