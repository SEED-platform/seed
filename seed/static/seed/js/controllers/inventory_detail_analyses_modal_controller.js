/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the analysis modal.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 *
 *
 */
angular.module('BE.seed.controller.inventory_detail_analyses_modal', [])
  .controller('inventory_detail_analyses_modal_controller', [
    '$scope',
    '$log',
    '$uibModalInstance',
    'Notification',
    'analyses_service',
    'inventory_ids',
    function (
      $scope,
      $log,
      $uibModalInstance,
      Notification,
      analyses_service,
      inventory_ids
    ) {
      $scope.inventory_count = inventory_ids.length
      // used to disable buttons on submit
      $scope.waiting_for_server = false

      $scope.new_analysis = {
        name: null,
        service: null,
        configuration: {}
      };

      $scope.bsyncr_models = [
        {model_type: 'Simple Linear Regression'},
        {model_type: 'Three Parameter Linear Model Cooling'},
        {model_type: 'Three Parameter Linear Model Heating'},
        {model_type: 'Four Parameter Linear Model'}
      ];

      $scope.better_savings_targets = [
        {savings_target: 'CONSERVATIVE'},
        {savings_target: 'NOMINAL'},
        {savings_target: 'AGGRESSIVE'}
      ];

      $scope.better_benchmark_options = [
        {benchmark_data: 'DEFAULT'},
        {benchmark_data: 'GENERATE'}
      ];

      $scope.initializeAnalysisConfig = () => {
        if ($scope.service == 'BSyncr') {
          $scope.new_analysis.configuration = {
            model: null
          }
        } else {
          $scope.new_analysis.configuration = {
            savings_target: null,
            benchmark_data: null,
            min_r_squared: null,
            portfolio_analysis: false,
          }
        }
      }

      /* Create a new analysis based on user input */
      $scope.submitNewAnalysisForm = function (form) {
        if (form.$invalid) {
          return;
        }
        $scope.waiting_for_server = true
        analyses_service.create_analysis(
          $scope.new_analysis.name,
          $scope.new_analysis.service,
          $scope.new_analysis.configuration,
          inventory_ids
        ).then(function (data) {
          $scope.waiting_for_server = false
          Notification.primary('Created Analysis');
          form.$setPristine();
          $scope.$close(data);
        }, function (response) {
          $scope.waiting_for_server = false
          $log.error('Error creating new analysis.', response);
          Notification.error('Failed to create Analysis: ' + response.data.message);
        });
      };

      /* User has cancelled dialog */
      $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
      };

    }]);
