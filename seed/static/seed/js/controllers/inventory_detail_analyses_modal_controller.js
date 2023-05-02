/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Controller for the analysis modal.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
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
    'cycles',
    function (
      $scope,
      $log,
      $uibModalInstance,
      Notification,
      analyses_service,
      inventory_ids,
      current_cycle,
      cycles,
    ) {
      $scope.inventory_count = inventory_ids.length;
      // used to disable buttons on submit
      $scope.waiting_for_server = false;
      $scope.cycles = cycles

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
      $scope.datePickersOpen = {
        start: false,
        end: false
      };
      $scope.invalidDates = false; // set this to true when startDate >= endDate;

      // Handle datepicker open/close events
      $scope.openStartDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.datePickersOpen.start = true;
      };
      $scope.openEndDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.datePickersOpen.end = true;
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
            $scope.new_analysis.configuration = {
              select_meters: 'all',
            };
            break;

          case 'CO2':
            $scope.new_analysis.configuration = {
              save_co2_results: true
            };
            break;

          case 'BETTER':
            $scope.new_analysis.configuration = {
              savings_target: null,
              benchmark_data_type: null,
              min_model_r_squared: null,
              portfolio_analysis: false,
              preprocess_meters: false,
              select_meters: 'all',
              enable_pvwatts: false,
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
        const { start_date, end_date } = $scope.new_analysis.configuration.meter ?? {};
        $scope.invalidDates = end_date < start_date;
      };

      $scope.changeCycle = (cycle_id) => {
        const selected_cycle = $scope.cycles.find(c => c.id == cycle_id)
        $scope.new_analysis.configuration.cycle_name = selected_cycle.name
      }
    }]);
