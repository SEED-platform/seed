/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    'current_cycle',
    function (
      $scope,
      $log,
      $uibModalInstance,
      Notification,
      analyses_service,
      inventory_ids,
      current_cycle
    ) {
      $scope.inventory_count = inventory_ids.length;
      // used to disable buttons on submit
      $scope.waiting_for_server = false;

      $scope.new_analysis = {
        name: null,
        service: null,
        configuration: {}
      };

      $scope.bsyncr_models = [
        'Simple Linear Regression',
        'Three Parameter Linear Model Cooling',
        'Three Parameter Linear Model Heating',
        'Four Parameter Linear Model'
      ];

      $scope.better_savings_targets = [
        'CONSERVATIVE',
        'NOMINAL',
        'AGGRESSIVE'
      ];

      $scope.better_benchmark_options = [
        'DEFAULT',
        'GENERATE'
      ];

      // Datepickers
      $scope.startDatePickerOpen = false;
      $scope.endDatePickerOpen = false;
      $scope.invalidDates = false; // set this to true when startDate >= endDate;

      // Handle datepicker open/close events
      $scope.openStartDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.startDatePickerOpen = true;
      };
      $scope.openEndDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.endDatePickerOpen = true;
      };

      // TODO:
      // if it's BETTER and selectMeters is 1
      // need to find start date and end date of meters data for first inventory?

      $scope.initializeAnalysisConfig = () => {
        switch ($scope.new_analysis.service) {

          case 'BSyncr':
            $scope.new_analysis.configuration = {
              model_type: null
            };
            break;

          case 'EUI':
            $scope.new_analysis.configuration = {};
            break;

          case 'CO2':
            $scope.new_analysis.configuration = {
              save_co2_results: true
            };
            break;

          case 'BETTER':
            $scope.new_analysis.configuration = {
              savings_target: null,
              benchmark_data: null,
              min_model_r_squared: null,
              portfolio_analysis: false,
              preprocess_meters: false,
              select_meters: 'select',
              meter: {
                start_date: null,
                end_date: null
              }
            };
            // if a cycle is selected, default inputs to cycle start/end
            if (('start' in current_cycle) && ('end' in current_cycle)) {
              $scope.new_analysis.configuration.meter.start_date = new Date(current_cycle.start);
              $scope.new_analysis.configuration.meter.end_date = new Date(current_cycle.end);
            }
            break;

          default:
            $log.error('Unknown analysis type.', $scope.new_analysis.service);
            Notification.error('Unknown analysis type: ' + $scope.new_analysis.service);

        }
      };

      /* Create a new analysis based on user input */
      $scope.submitNewAnalysisForm = function (form) {
        if (form.$invalid) {
          return;
        }
        $scope.waiting_for_server = true;

        analyses_service.create_analysis(
          $scope.new_analysis.name,
          $scope.new_analysis.service,
          $scope.new_analysis.configuration,
          inventory_ids
        ).then(function (data) {
          $scope.waiting_for_server = false;
          Notification.primary('Created Analysis');
          form.$setPristine();
          $scope.$close(data);
        }, function (response) {
          $scope.waiting_for_server = false;
          $log.error('Error creating new analysis.', response);
          Notification.error('Failed to create Analysis: ' + response.data.message);
        });
      };

      /* User has cancelled dialog */
      $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
      };

      $scope.$watch('new_analysis.configuration.meter.start_date', function () {
        $scope.checkInvalidDate();
      });

      $scope.$watch('new_analysis.configuration.meter.end_date', function ( ) {
        $scope.checkInvalidDate();
      });

      $scope.checkInvalidDate = function () {
        $scope.invalidDates = ($scope.new_analysis.configuration.meter.end_date < $scope.new_analysis.configuration.meter.start_date);
      };

    }]);
