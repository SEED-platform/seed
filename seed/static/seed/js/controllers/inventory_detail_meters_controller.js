angular.module('BE.seed.controller.inventory_detail_meters', [])
  .controller('inventory_detail_meters_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'meter_service',
    'cycles',
    'dataset_service',
    'inventory_service',
    'inventory_payload',
    'meters',
    'property_meter_usage',
    'spinner_utility',
    'urls',
    'user_service',
    'organization_payload',
    '$log',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      $window,
      meter_service,
      cycles,
      dataset_service,
      inventory_service,
      inventory_payload,
      meters,
      property_meter_usage,
      spinner_utility,
      urls,
      user_service,
      organization_payload,
      $log
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = organization_payload.organization;
      $scope.filler_cycle = cycles.cycles[0].id;
      $scope.scenarios = _.uniqBy(_.map(meters, function (meter) {
        return {
          id: meter.scenario_id,
          name: meter.scenario_name
        };
      }), 'id').filter(function (scenario) {
        return !_.isNil(scenario.id);
      });

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      var getMeterLabel = function (meter) {
        return meter.type + ' - ' + meter.source + ' - ' + meter.source_id;
      };

      var resetSelections = function () {
        $scope.meter_selections = _.map(sorted_meters, function (meter) {
          return {
            selected: true,
            label: getMeterLabel(meter),
            value: meter.id
          };
        });

        $scope.scenario_selections = _.map($scope.scenarios, function (scenario) {
          return {
            selected: true,
            label: scenario.name,
            value: scenario.id
          };
        });
      };

      // On page load, all meters and readings
      $scope.data = property_meter_usage.readings;
      $scope.has_readings = $scope.data.length > 0;

      var sorted_meters = _.sortBy(meters, ['source', 'source_id', 'type']);
      resetSelections();

      $scope.meter_selection_toggled = function (is_open) {
        if (!is_open) {
          $scope.applyFilters();
        }
      };

      $scope.scenario_selection_toggled = function (is_open) {
        if (!is_open) {
          $scope.applyFilters();
        }
      };

      $scope.gridOptions = {
        data: 'data',
        columnDefs: property_meter_usage.column_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };

      $scope.apply_column_settings = function () {
        _.forEach($scope.gridOptions.columnDefs, function (column) {
          column.enableHiding = false;
          column.enableColumnResizing = true;

          if (column.field === 'year') {
            // Filter years like integers
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type === 'reading') {
            column.cellFilter = 'number: 2';
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type === 'datetime') {
            column.filter = inventory_service.dateFilter();
          }
        });
      };

      $scope.apply_column_settings();

      // Ideally, these should be translatable, but the "selected" property
      // should always be in English as this gets sent to BE.
      $scope.interval = {
        options: [
          'Exact',
          'Month',
          'Year'
        ],
        selected: 'Exact'
      };

      $scope.filterMethod = {
        options: [
          'meter',
          'scenario'
        ],
        selected: 'meter'
      };
      // remove option to filter by scenario if there are no scenarios
      if ($scope.scenarios.length === 0) {
        $scope.filterMethod.options = ['meter'];
      }

      // given a list of meter labels, it returns the filtered readings and column defs
      // This is used by the primary filterBy... functions
      var filterByMeterLabels = function filterByMeterLabels (readings, columnDefs, meterLabels) {
        var timeColumns = ['start_time', 'end_time', 'month', 'year'];
        var selectedColumns = meterLabels.concat(timeColumns);
        var filteredReadings = readings.map(function (reading) {
          return Object.entries(reading).reduce(function (newReading, _ref) {
            var key = _ref[0],
              value = _ref[1];

            if (selectedColumns.includes(key)) {
              newReading[key] = value;
            }

            return newReading;
          }, {});
        });
        var filteredColumnDefs = columnDefs.filter(function (columnDef) {
          return selectedColumns.includes(columnDef.field);
        });
        return {
          readings: filteredReadings,
          columnDefs: filteredColumnDefs
        };
      };

      // given the meter selections, it returns the filtered readings and column defs
      var filterByMeterSelections = function (readings, columnDefs, meterSelections) {
        // filter according to meter selections
        var selectedMeterLabels = meterSelections.filter(function (selection) {
          return selection.selected;
        })
          .map(function (selection) {
            return selection.label;
          });

        return filterByMeterLabels(readings, columnDefs, selectedMeterLabels);
      };

      // given the scenario selections, it returns the filtered readings and column defs
      var filterByScenarioSelections = function (readings, columnDefs, meters, scenarioSelections) {
        var selectedScenarioIds = scenarioSelections.filter(function (selection) {
          return selection.selected;
        }).map(function (selection) {
          return selection.value;
        });
        var selectedMeterLabels = meters.filter(function (meter) {
          return selectedScenarioIds.includes(meter.scenario_id);
        }).map(function (meter) {
          return getMeterLabel(meter);
        });

        return filterByMeterLabels(readings, columnDefs, selectedMeterLabels);
      };

      // filters the meter readings by selected meters or scenarios and updates the table
      $scope.applyFilters = function () {
        var results, readings, columnDefs;
        if ($scope.filterMethod.selected === 'meter') {
          results = filterByMeterSelections(property_meter_usage.readings, property_meter_usage.column_defs, $scope.meter_selections);
          readings = results.readings;
          columnDefs = results.columnDefs;
        } else if ($scope.filterMethod.selected === 'scenario') {
          results = filterByScenarioSelections(property_meter_usage.readings, property_meter_usage.column_defs, sorted_meters, $scope.scenario_selections);
          readings = results.readings;
          columnDefs = results.columnDefs;
        } else {
          $log.error('Invalid filter method selected: ', $scope.filterMethod);
          return;
        }

        $scope.data = readings;
        $scope.gridOptions.columnDefs = columnDefs;
        $scope.has_readings = $scope.data.length > 0;
        $scope.apply_column_settings();
      };

      // refresh_readings make an API call to refresh the base readings data
      // according to the selected interval
      $scope.refresh_readings = function () {
        spinner_utility.show();
        meter_service.property_meter_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          [] // Not excluding any meters from the query
        ).then(function (usage) {
          // update the base data and reset filters
          property_meter_usage = usage;

          resetSelections();
          $scope.applyFilters();
          spinner_utility.hide();
        });
      };

      $scope.open_green_button_upload_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/green_button_upload_modal.html',
          controller: 'green_button_upload_modal_controller',
          resolve: {
            filler_cycle: function () {
              return $scope.filler_cycle;
            },
            organization_id: function () {
              return $scope.organization.id;
            },
            view_id: function () {
              return $scope.inventory.view_id;
            },
            datasets: function () {
              return dataset_service.get_datasets().then(function (result) {
                return result.datasets;
              });
            }
          }
        });
      };

      $scope.inventory_display_name = function (property_type) {
        let error = '';
        let field = property_type == 'property' ? $scope.organization.property_display_field : $scope.organization.taxlot_display_field;
        if (!(field in $scope.item_state)) {
          error = field + ' does not exist';
          field = 'address_line_1';
        }
        if (!$scope.item_state[field]) {
          error += (error == '' ? '' : ' and default ') + field + ' is blank';
        }
        $scope.inventory_name = $scope.item_state[field] ? $scope.item_state[field] : '(' + error + ') <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>';
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };
    }]);
