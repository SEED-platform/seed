/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.compliance_setup', []).controller('compliance_setup_controller', [
  '$scope',
  '$stateParams',
  'compliance_metric_service',
  // 'property_columns',
  'organization_payload',
  'query_threshold_payload',
  'shared_fields_payload',
  'auth_payload',
  'organization_service',
  '$filter',
  function (
    $scope,
    $stateParams,
    compliance_metric_service,
    // property_columns,
    organization_payload,
    query_threshold_payload,
    shared_fields_payload,
    auth_payload,
    organization_service,
    $filter
  ) {
    // $scope.fields = property_columns;
    $scope.org = organization_payload.organization;
    $scope.filter_params = {};
    $scope.org.query_threshold = query_threshold_payload.query_threshold;
    $scope.auth = auth_payload.auth;
    // $scope.infinite_fields = $scope.fields.slice(0, 20);
    $scope.controls = {
      select_all: false
    };

            // load source columns
            // $scope.source_columns = {
            //   'property': property_columns,
            //   'by_id': Object.assign(_collect_array_as_object(property_columns))
            // };
    
    // $scope.$watch('filter_params.title', function () {
    //   if (!$scope.filter_params.title) {
    //     $scope.controls.select_all = false;
    //   }
    // });

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.org.public_fields = $scope.fields.filter(function (f) {
        return f.public_checked;
      });
      organization_service.save_org_settings($scope.org).then(function () {
        $scope.settings_updated = true;
      }, function (data) {
        $scope.$emit('app_error', data);
      });
    };

    /**
     * preforms from initial data processing:
     * - sets the checked shared fields
     */
  //   var init = function () {
  //     var public_columns = shared_fields_payload.public_fields.map(function (f) {
  //       return f.name;
  //     });
  //     $scope.fields = $scope.fields.map(function (f) {
  //       if (_.includes(public_columns, f.name)) {
  //         f.public_checked = true;
  //       }
  //       return f;
  //     });
  //   };
  //   init();

  }]);
