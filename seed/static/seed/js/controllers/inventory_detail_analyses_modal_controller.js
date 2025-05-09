/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * Controller for the analysis modal.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 */
angular.module('SEED.controller.inventory_detail_analyses_modal', []).controller('inventory_detail_analyses_modal_controller', [
  '$scope',
  '$sce',
  '$log',
  '$uibModalInstance',
  'Notification',
  'analyses_service',
  'inventory_ids',
  'property_columns',
  'current_cycle',
  'cycles',
  'user',
  // eslint-disable-next-line func-names
  function ($scope, $sce, $log, $uibModalInstance, Notification, analyses_service, inventory_ids, property_columns, current_cycle, cycles, user) {
    $scope.inventory_count = inventory_ids.length;
    // used to disable buttons on submit
    $scope.waiting_for_server = false;
    $scope.cycles = cycles;
    $scope.user = user;
    $scope.property_columns = property_columns;
    $scope.eui_columns = $scope.property_columns.filter((o) => o.data_type === 'eui');

    $scope.new_analysis = {
      name: null,
      service: null,
      configuration: {}
    };

    $scope.bsyncr_models = ['Simple Linear Regression', 'Three Parameter Linear Model Cooling', 'Three Parameter Linear Model Heating', 'Four Parameter Linear Model'];

    $scope.better_savings_targets = ['CONSERVATIVE', 'NOMINAL', 'AGGRESSIVE'];

    $scope.better_benchmark_options = ['DEFAULT', 'GENERATE'];

    $scope.current_cycle = current_cycle;

    // Datepickers
    $scope.datePickersOpen = {
      start: false,
      end: false
    };
    $scope.invalidDates = false; // set this to true when startDate >= endDate;

    // Handle datepicker open/close events
    $scope.openStartDatePicker = ($event) => {
      $event.preventDefault();
      $event.stopPropagation();
      $scope.datePickersOpen.start = true;
    };
    $scope.openEndDatePicker = ($event) => {
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
            // cycle_id is ignored unless select_meters: 'select_cycle'
            cycle_id: current_cycle.id
          };
          break;

        case 'CO2':
          $scope.new_analysis.configuration = {
            save_co2_results: false
          };
          // only root users can create columns
          if (user.is_ali_root && ['member', 'owner'].includes(user.organization.user_role)) {
            $scope.new_analysis.configuration.save_co2_results = true;
          }
          break;

        case 'BETTER':
          $scope.new_analysis.configuration = {
            savings_target: null,
            benchmark_data_type: null,
            min_model_r_squared: null,
            portfolio_analysis: false,
            preprocess_meters: false,
            select_meters: 'select_cycle',
            cycle_id: current_cycle.id,
            enable_pvwatts: false,
            meter: {
              start_date: null,
              end_date: null
            }
          };
          // if a cycle is selected, default inputs to cycle start/end
          if ('start' in current_cycle && 'end' in current_cycle) {
            $scope.new_analysis.configuration.meter.start_date = new Date(current_cycle.start);
            $scope.new_analysis.configuration.meter.end_date = new Date(current_cycle.end);
          }
          break;
        case 'EEEJ':
          $scope.new_analysis.configuration = {};
          break;
        case 'Element Statistics':
          $scope.new_analysis.configuration = {};
          break;
        case 'Building Upgrade Recommendation':
          $scope.new_analysis.configuration = {
            column_params: {
              total_eui: null,
              gas_eui: null,
              electric_eui: null,
              target_gas_eui: null,
              target_electric_eui: null,
              condition_index: null,
              has_bas: null
            },
            total_eui_goal: null,
            ff_eui_goal: null,
            year_built_threshold: null,
            fair_actual_to_benchmark_eui_ratio: null,
            poor_actual_to_benchmark_eui_ratio: null,
            building_sqft_threshold: null,
            condition_index_threshold: null,
            ff_fired_equipment_rsl_threshold: null
          };
          break;
        default:
          $log.error('Unknown analysis type.', $scope.new_analysis.service);
          Notification.error(`Unknown analysis type: ${$scope.new_analysis.service}`);
      }
    };

    /* Create a new analysis based on user input */
    $scope.submitNewAnalysisForm = (form) => {
      if (form.$invalid) {
        return;
      }
      $scope.waiting_for_server = true;

      analyses_service.create_analysis($scope.new_analysis.name, $scope.new_analysis.service, $scope.new_analysis.configuration, inventory_ids, window.SEED.access_level_instance_id).then(
        (data) => {
          $scope.waiting_for_server = false;
          Notification.primary('Created Analysis');
          form.$setPristine();
          $scope.$close(data);
        },
        (response) => {
          $scope.waiting_for_server = false;
          $scope.error = linkify(response.data.message);
          $log.error('Error creating new analysis:', response);
          Notification.error(`Failed to create Analysis: ${$scope.error}`);
        }
      );
    };

    const linkify = (text) => {
      // Regular expression matching any URL starting with http:// or https://
      const urlPattern = /(\b(https?):\/\/[-A-Z0-9+&@#/%?=~_|!:,.;]*[-A-Z0-9+&@#/%=~_|])/ig;

      // Add link html
      const linkedText = text.replace(urlPattern, '<a href="$1" target="_blank">$1</a>');
      return $sce.trustAsHtml(linkedText);
    };

    /* User has cancelled dialog */
    $scope.cancel = () => {
      // don't do anything, just close modal.
      $uibModalInstance.dismiss('cancel');
    };

    $scope.$watch('new_analysis.configuration.meter.start_date', () => {
      $scope.checkInvalidDate();
    });

    $scope.$watch('new_analysis.configuration.meter.end_date', () => {
      $scope.checkInvalidDate();
    });

    $scope.checkInvalidDate = () => {
      const { start_date, end_date } = $scope.new_analysis.configuration.meter ?? {};
      $scope.invalidDates = end_date < start_date;
    };

    $scope.changeCycle = (cycle_id) => {
      const selected_cycle = $scope.cycles.find((c) => c.id === cycle_id);
      $scope.new_analysis.configuration.cycle_name = selected_cycle.name;
    };
  }
]);
