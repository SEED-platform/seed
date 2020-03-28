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
      $log,
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();
      $scope.filler_cycle = cycles.cycles[0].id;
      $scope.scenarios = _.uniqBy(_.map(meters, function(meter) {
        return {
          id: meter.scenario_id,
          name: meter.scenario_name
        }
      }), 'id').filter(scenario => scenario.id !== undefined && scenario.id !== null)

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      const getMeterLabel = (meter) => {
        return meter.type + ' - ' + meter.source + ' - ' + meter.source_id
      }

      const resetSelections = () => {
        $scope.meter_selections = _.map(sorted_meters, function(meter) {
          return {
            selected: true,
            label: getMeterLabel(meter),
            value: meter.id
          };
        });

        $scope.scenario_selections = _.map($scope.scenarios, function(scenario) {
          return {
            selected: true,
            label: scenario.name,
            value: scenario.id
          }
        });
      }

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

      $scope.scenario_selection_toggled = (is_open) => {
        if (!is_open) {
          $scope.applyFilters()
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
        $scope.filterMethod.options = ['meter']
      }

      // given a list of meter labels, it returns the filtered readings and column defs
      // This is used by the primary filterBy... functions
      const filterByMeterLabels = (readings, columnDefs, meterLabels) => {
        const timeColumns = ['start_time', 'end_time', 'month', 'year']
        const selectedColumns = meterLabels.concat(timeColumns)

        const filteredReadings = readings.map(reading => Object.entries(reading).reduce((newReading, [key, value]) => {
          if (selectedColumns.includes(key)) {
            newReading[key] = value;
          }
          return newReading;
        }, {}));

        const filteredColumnDefs = columnDefs.filter(columnDef => selectedColumns.includes(columnDef.field))
        return { readings: filteredReadings, columnDefs: filteredColumnDefs}
      }

      // given the meter selections, it returns the filtered readings and column defs
      const filterByMeterSelections = (readings, columnDefs, meterSelections) => {
        // filter according to meter selections
        const selectedMeterLabels = meterSelections.filter(selection => selection.selected)
                                                   .map(selection => selection.label);

        return filterByMeterLabels(readings, columnDefs, selectedMeterLabels)
      }

      // given the scenario selections, it returns the filtered readings and column defs
      const filterByScenarioSelections = (readings, columnDefs, meters, scenarioSelections) => {
        const selectedScenarioIds = scenarioSelections.filter(selection => selection.selected).map(selection => selection.value);
        const selectedMeterLabels = meters.filter(meter => selectedScenarioIds.includes(meter.scenario_id))
                                          .map(meter => getMeterLabel(meter))

        return filterByMeterLabels(readings, columnDefs, selectedMeterLabels)
      }

      // filters the meter readings by selected meters or scenarios and updates the table
      $scope.applyFilters = () => {
        let readings, columnDefs;
        if ($scope.filterMethod.selected === 'meter') {
          ({readings, columnDefs} = filterByMeterSelections(
            property_meter_usage.readings,
            property_meter_usage.column_defs,
            $scope.meter_selections
          ))
        } else if ($scope.filterMethod.selected === 'scenario') {
          ({readings, columnDefs} = filterByScenarioSelections(
            property_meter_usage.readings,
            property_meter_usage.column_defs,
            sorted_meters,
            $scope.scenario_selections
          ))
        } else {
          $log.error("Invalid filter method selected: ", $scope.filterMethod)
          return
        }

        $scope.data = readings;
        $scope.gridOptions.columnDefs = columnDefs;
        $scope.has_readings = $scope.data.length > 0;
        $scope.apply_column_settings();
      }

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
